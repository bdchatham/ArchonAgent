import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { ArchonConfig } from './config-loader';
import { ArchonInfrastructureStack } from './archon-infrastructure-stack';
import { ArchonLambdaLayer } from './archon-lambda-layer';

/**
 * Props for ArchonKnowledgeBaseStack
 */
export interface ArchonKnowledgeBaseStackProps extends cdk.StackProps {
  config: ArchonConfig;
  environment?: string;
  infrastructure: ArchonInfrastructureStack;
}

/**
 * Knowledge Base Stack for Archon Agent
 * 
 * This stack manages the knowledge base ingestion and maintenance:
 * - EventBridge scheduled rule for periodic document monitoring
 * - Lambda function to monitor GitHub repositories for changes
 * - DynamoDB table for tracking document versions
 * - IAM roles with least-privilege access to Bedrock, OpenSearch, and DynamoDB
 * 
 * Follows AWS Well-Architected Framework principles:
 * - Security: Least-privilege IAM, encryption at rest, no hardcoded credentials
 * - Reliability: Automatic retries, error handling, CloudWatch alarms
 * - Performance: Configurable Lambda memory and timeout
 * - Cost Optimization: Serverless architecture, pay-per-use
 * - Operational Excellence: CloudWatch logging, metrics, and alarms
 */
export class ArchonKnowledgeBaseStack extends cdk.Stack {
  public readonly monitorFunction: lambda.Function;
  public readonly changeTrackerTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: ArchonKnowledgeBaseStackProps) {
    super(scope, id, props);

    const environment = props.environment || 'dev';
    const config = props.config;
    const infrastructure = props.infrastructure;

    // Create Lambda layer with shared dependencies
    const lambdaLayer = new ArchonLambdaLayer(this, 'LambdaLayer', environment);

    // DynamoDB table for tracking document changes
    // Stores SHA hashes and timestamps to detect when documents are modified
    this.changeTrackerTable = new dynamodb.Table(this, 'ChangeTrackerTable', {
      tableName: `archon-document-tracker-${environment}`,
      partitionKey: {
        name: 'repo_file_path',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // Apply tags to DynamoDB table
    cdk.Tags.of(this.changeTrackerTable).add('Environment', environment);
    cdk.Tags.of(this.changeTrackerTable).add('Project', 'Archon');
    cdk.Tags.of(this.changeTrackerTable).add('Owner', 'ArchonTeam');

    // CloudWatch log group for Lambda function
    const logGroup = new logs.LogGroup(this, 'MonitorLogGroup', {
      logGroupName: `/aws/lambda/archon-monitor-${environment}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // IAM role for Lambda function with least-privilege permissions
    const lambdaRole = new iam.Role(this, 'MonitorLambdaRole', {
      roleName: `ArchonMonitorLambda-${environment}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Execution role for Archon document monitor Lambda',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });

    // Grant DynamoDB permissions
    this.changeTrackerTable.grantReadWriteData(lambdaRole);

    // Grant Bedrock permissions for embeddings
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel'
      ],
      resources: [
        `arn:aws:bedrock:${this.region}::foundation-model/${config.models.embedding_model}`
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

    // Lambda function for document monitoring
    // Uses Lambda layer for shared dependencies (langchain, opensearch-py, PyGithub)
    // Application code is bundled separately for faster deployments
    this.monitorFunction = new lambda.Function(this, 'MonitorFunction', {
      functionName: `archon-monitor-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda.monitor.document_monitor.lambda_handler',
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
        DYNAMODB_TABLE: this.changeTrackerTable.tableName,
        OPENSEARCH_ENDPOINT: infrastructure.collectionEndpoint,
        OPENSEARCH_INDEX: `archon-docs-${environment}`,
        EMBEDDING_MODEL: config.models.embedding_model,
        VECTOR_DIMENSIONS: config.infrastructure.vector_db_dimensions.toString(),
        CONFIG_PATH: '/var/task/config/config.example.yaml',
        ENVIRONMENT: environment,
        LOG_LEVEL: 'INFO',
        XRAY_ENABLED: 'true'
      },
      logGroup: logGroup,
      description: 'Monitors GitHub repositories for .kiro/ documentation changes',
      tracing: lambda.Tracing.ACTIVE
    });

    // EventBridge rule for scheduled execution
    const scheduleRule = new events.Rule(this, 'MonitorSchedule', {
      ruleName: `archon-monitor-schedule-${environment}`,
      description: 'Triggers Archon document monitor on a schedule',
      schedule: events.Schedule.expression(config.infrastructure.cron_schedule)
    });

    // Add Lambda as target for the schedule
    scheduleRule.addTarget(new targets.LambdaFunction(this.monitorFunction, {
      retryAttempts: 2
    }));

    // CloudWatch alarm for Lambda errors
    const errorAlarm = this.monitorFunction.metricErrors({
      period: cdk.Duration.minutes(5),
      statistic: 'Sum'
    }).createAlarm(this, 'MonitorErrorAlarm', {
      alarmName: `archon-monitor-errors-${environment}`,
      alarmDescription: 'Alarm when Archon monitor Lambda has errors',
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // CloudWatch alarm for Lambda duration (approaching timeout)
    const durationAlarm = this.monitorFunction.metricDuration({
      period: cdk.Duration.minutes(5),
      statistic: 'Maximum'
    }).createAlarm(this, 'MonitorDurationAlarm', {
      alarmName: `archon-monitor-duration-${environment}`,
      alarmDescription: 'Alarm when Archon monitor Lambda approaches timeout',
      threshold: config.infrastructure.lambda_timeout * 1000 * 0.9, // 90% of timeout in ms
      evaluationPeriods: 1,
      treatMissingData: cdk.aws_cloudwatch.TreatMissingData.NOT_BREACHING
    });

    // CloudFormation outputs
    new cdk.CfnOutput(this, 'MonitorFunctionArn', {
      value: this.monitorFunction.functionArn,
      description: 'ARN of the document monitor Lambda function',
      exportName: `${this.stackName}-MonitorFunctionArn`
    });

    new cdk.CfnOutput(this, 'ChangeTrackerTableName', {
      value: this.changeTrackerTable.tableName,
      description: 'Name of the DynamoDB change tracker table',
      exportName: `${this.stackName}-ChangeTrackerTableName`
    });

    new cdk.CfnOutput(this, 'ScheduleRuleName', {
      value: scheduleRule.ruleName,
      description: 'Name of the EventBridge schedule rule',
      exportName: `${this.stackName}-ScheduleRuleName`
    });

    // Apply tags to all resources in the stack
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Project', 'Archon');
    cdk.Tags.of(this).add('Owner', 'ArchonTeam');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');
  }
}
