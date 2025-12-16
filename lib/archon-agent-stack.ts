import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { ArchonConfig } from './config-loader';
import { ArchonInfrastructureStack } from './archon-infrastructure-stack';
import { ArchonLambdaLayer } from './archon-lambda-layer';

/**
 * Props for ArchonAgentStack
 */
export interface ArchonAgentStackProps extends cdk.StackProps {
  config: ArchonConfig;
  environment?: string;
  infrastructure: ArchonInfrastructureStack;
}

/**
 * Agent Stack for Archon
 * 
 * This stack implements the Archon agent query processing:
 * - API Gateway REST API for query endpoint
 * - Lambda function for RAG-based query processing
 * - IAM roles with least-privilege access to Bedrock and OpenSearch
 * 
 * Follows AWS Well-Architected Framework principles:
 * - Security: Least-privilege IAM, CORS configuration, API throttling
 * - Reliability: Automatic retries, error handling, CloudWatch alarms
 * - Performance: Configurable Lambda memory and timeout, API caching
 * - Cost Optimization: Serverless architecture, pay-per-use
 * - Operational Excellence: CloudWatch logging, metrics, and alarms
 */
export class ArchonAgentStack extends cdk.Stack {
  public readonly queryFunction: lambda.Function;
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ArchonAgentStackProps) {
    super(scope, id, props);

    const environment = props.environment || 'dev';
    const config = props.config;
    const infrastructure = props.infrastructure;

    // Create Lambda layer with shared dependencies
    const lambdaLayer = new ArchonLambdaLayer(this, 'LambdaLayer', environment);

    // CloudWatch log group for Lambda function
    const logGroup = new logs.LogGroup(this, 'QueryLogGroup', {
      logGroupName: `/aws/lambda/archon-query-${environment}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // IAM role for Lambda function with least-privilege permissions
    const lambdaRole = new iam.Role(this, 'QueryLambdaRole', {
      roleName: `ArchonQueryLambda-${environment}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Execution role for Archon query handler Lambda',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });

    // Grant Bedrock permissions for embeddings and LLM
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel'
      ],
      resources: [
        `arn:aws:bedrock:${this.region}::foundation-model/${config.models.embedding_model}`,
        `arn:aws:bedrock:${this.region}::foundation-model/${config.models.llm_model}`
      ]
    }));

    // Grant OpenSearch Serverless permissions
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'aoss:APIAccessAll'
      ],
      resources: [infrastructure.collectionArn]
    }));

    // Lambda function for query processing
    // Uses Lambda layer for shared dependencies (langchain, opensearch-py, PyGithub)
    // Application code is bundled separately for faster deployments
    this.queryFunction = new lambda.Function(this, 'QueryFunction', {
      functionName: `archon-query-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda.query.query_handler.lambda_handler',
      code: lambda.Code.fromAsset('.', {
        exclude: [
          'node_modules',
          'cdk.out',
          '.git',
          '.hypothesis',
          '.pytest_cache',
          'venv',
          'tests',
          'lambda-layer',
          'scripts',
          '*.md',
          '*.ts',
          '*.js',
          '*.json',
          'bin',
          'lib'
        ]
      }),
      layers: [lambdaLayer.layer],
      role: lambdaRole,
      timeout: cdk.Duration.seconds(config.infrastructure.lambda_timeout),
      memorySize: config.infrastructure.lambda_memory,
      environment: {
        OPENSEARCH_ENDPOINT: infrastructure.collectionEndpoint,
        OPENSEARCH_INDEX: `archon-docs-${environment}`,
        EMBEDDING_MODEL: config.models.embedding_model,
        LLM_MODEL: config.models.llm_model,
        LLM_TEMPERATURE: config.models.llm_temperature.toString(),
        MAX_TOKENS: config.models.max_tokens.toString(),
        RETRIEVAL_K: config.models.retrieval_k.toString(),
        VECTOR_DIMENSIONS: config.infrastructure.vector_db_dimensions.toString(),
        ENVIRONMENT: environment,
        LOG_LEVEL: 'INFO',
        XRAY_ENABLED: 'true'
      },
      logGroup: logGroup,
      description: 'Processes queries using RAG with Bedrock and OpenSearch',
      tracing: lambda.Tracing.ACTIVE
    });

    // API Gateway REST API
    this.api = new apigateway.RestApi(this, 'ArchonApi', {
      restApiName: `archon-api-${environment}`,
      description: 'Archon agent query API',
      deployOptions: {
        stageName: environment,
        throttlingRateLimit: 1, // 1 request per second for personal use
        throttlingBurstLimit: 2, // Allow small burst of 2 requests
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token'
        ],
        allowCredentials: true
      },
      cloudWatchRole: true
    });

    // Create OpenAI-compatible endpoint structure: /v1/chat/completions
    // This allows Archon to work with OpenAI-compatible clients and tools
    // The Lambda handler will translate between OpenAI format and Archon's internal format
    const v1Resource = this.api.root.addResource('v1');
    const chatResource = v1Resource.addResource('chat');
    const completionsResource = chatResource.addResource('completions');
    
    // Lambda integration
    const completionsIntegration = new apigateway.LambdaIntegration(this.queryFunction, {
      proxy: true,
      integrationResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'"
          }
        }
      ]
    });

    // POST /v1/chat/completions method (OpenAI-compatible)
    completionsResource.addMethod('POST', completionsIntegration, {
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true
          }
        }
      ],
      requestValidator: new apigateway.RequestValidator(this, 'CompletionsRequestValidator', {
        restApi: this.api,
        requestValidatorName: 'completions-validator',
        validateRequestBody: true,
        validateRequestParameters: false
      }),
      requestModels: {
        'application/json': new apigateway.Model(this, 'CompletionsRequestModel', {
          restApi: this.api,
          contentType: 'application/json',
          modelName: 'ChatCompletionRequest',
          schema: {
            type: apigateway.JsonSchemaType.OBJECT,
            properties: {
              messages: {
                type: apigateway.JsonSchemaType.ARRAY,
                items: {
                  type: apigateway.JsonSchemaType.OBJECT,
                  properties: {
                    role: {
                      type: apigateway.JsonSchemaType.STRING,
                      enum: ['system', 'user', 'assistant']
                    },
                    content: {
                      type: apigateway.JsonSchemaType.STRING
                    }
                  },
                  required: ['role', 'content']
                },
                minItems: 1
              },
              model: {
                type: apigateway.JsonSchemaType.STRING
              },
              temperature: {
                type: apigateway.JsonSchemaType.NUMBER,
                minimum: 0,
                maximum: 2
              },
              max_tokens: {
                type: apigateway.JsonSchemaType.INTEGER,
                minimum: 1
              }
            },
            required: ['messages']
          }
        })
      }
    });

    // CloudWatch alarm for Lambda errors
    const errorAlarm = this.queryFunction.metricErrors({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum'
    }).createAlarm(this, 'QueryErrorAlarm', {
      alarmName: `archon-query-errors-${environment}`,
      alarmDescription: 'Alarm when Archon query Lambda has errors',
      threshold: 5,
      evaluationPeriods: 1,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // CloudWatch alarm for Lambda duration (approaching timeout)
    const durationAlarm = this.queryFunction.metricDuration({
      period: cdk.Duration.minutes(5),
      statistic: 'Maximum'
    }).createAlarm(this, 'QueryDurationAlarm', {
      alarmName: `archon-query-duration-${environment}`,
      alarmDescription: 'Alarm when Archon query Lambda approaches timeout',
      threshold: config.infrastructure.lambda_timeout * 1000 * 0.9, // 90% of timeout in ms
      evaluationPeriods: 1,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // CloudWatch alarm for API Gateway 5xx errors
    const apiErrorAlarm = this.api.metricServerError({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum'
    }).createAlarm(this, 'ApiErrorAlarm', {
      alarmName: `archon-api-5xx-${environment}`,
      alarmDescription: 'Alarm when API Gateway has 5xx errors',
      threshold: 5,
      evaluationPeriods: 1,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // CloudWatch alarm for API Gateway latency
    const latencyAlarm = this.api.metricLatency({
      period: cdk.Duration.minutes(5),
      statistic: 'Average'
    }).createAlarm(this, 'ApiLatencyAlarm', {
      alarmName: `archon-api-latency-${environment}`,
      alarmDescription: 'Alarm when API Gateway latency is high',
      threshold: 5000, // 5 seconds
      evaluationPeriods: 2,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // CloudFormation outputs
    new cdk.CfnOutput(this, 'QueryFunctionArn', {
      value: this.queryFunction.functionArn,
      description: 'ARN of the query handler Lambda function',
      exportName: `${this.stackName}-QueryFunctionArn`
    });

    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
      description: 'URL of the Archon API Gateway',
      exportName: `${this.stackName}-ApiEndpoint`
    });

    new cdk.CfnOutput(this, 'ChatCompletionsEndpoint', {
      value: `${this.api.url}v1/chat/completions`,
      description: 'OpenAI-compatible chat completions endpoint',
      exportName: `${this.stackName}-ChatCompletionsEndpoint`
    });

    // Apply tags to all resources in the stack
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Project', 'Archon');
    cdk.Tags.of(this).add('Owner', 'ArchonTeam');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');
  }
}
