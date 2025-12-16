import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

/**
 * Props for ArchonMonitoringDashboard
 */
export interface ArchonMonitoringDashboardProps {
  environment: string;
  monitorFunction?: lambda.Function;
  queryFunction?: lambda.Function;
  api?: apigateway.RestApi;
  changeTrackerTable?: dynamodb.Table;
}

/**
 * CloudWatch Dashboard for Archon System Monitoring
 * 
 * Provides comprehensive visibility into:
 * - Lambda function performance and errors
 * - API Gateway metrics
 * - Custom application metrics
 * - DynamoDB operations
 * - Document processing pipeline
 * - Query processing pipeline
 */
export class ArchonMonitoringDashboard extends Construct {
  public readonly dashboard: cloudwatch.Dashboard;

  constructor(scope: Construct, id: string, props: ArchonMonitoringDashboardProps) {
    super(scope, id);

    const { environment, monitorFunction, queryFunction, api, changeTrackerTable } = props;

    // Create dashboard
    this.dashboard = new cloudwatch.Dashboard(this, 'Dashboard', {
      dashboardName: `Archon-${environment}`,
      periodOverride: cloudwatch.PeriodOverride.AUTO
    });

    // === OVERVIEW ROW ===
    const overviewWidgets: cloudwatch.IWidget[] = [];

    // System health indicator
    if (monitorFunction && queryFunction) {
      overviewWidgets.push(
        new cloudwatch.SingleValueWidget({
          title: 'System Health',
          width: 6,
          height: 3,
          metrics: [
            monitorFunction.metricErrors({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
            queryFunction.metricErrors({ statistic: 'Sum', period: cdk.Duration.hours(1) })
          ]
        })
      );
    }

    // Total queries processed (last hour)
    overviewWidgets.push(
      new cloudwatch.SingleValueWidget({
        title: 'Queries (Last Hour)',
        width: 6,
        height: 3,
        metrics: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'QueriesProcessed',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum',
            period: cdk.Duration.hours(1)
          })
        ]
      })
    );

    // Documents processed (last hour)
    overviewWidgets.push(
      new cloudwatch.SingleValueWidget({
        title: 'Documents Processed (Last Hour)',
        width: 6,
        height: 3,
        metrics: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'DocumentsProcessed',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum',
            period: cdk.Duration.hours(1)
          })
        ]
      })
    );

    // Average query latency
    overviewWidgets.push(
      new cloudwatch.SingleValueWidget({
        title: 'Avg Query Latency (Last Hour)',
        width: 6,
        height: 3,
        metrics: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'QueryLatency',
            dimensionsMap: { Environment: environment },
            statistic: 'Average',
            period: cdk.Duration.hours(1),
            unit: cloudwatch.Unit.SECONDS
          })
        ]
      })
    );

    if (overviewWidgets.length > 0) {
      this.dashboard.addWidgets(...overviewWidgets);
    }

    // === LAMBDA FUNCTIONS ROW ===
    const lambdaWidgets: cloudwatch.IWidget[] = [];

    if (monitorFunction) {
      // Monitor function invocations
      lambdaWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'Monitor Function - Invocations',
          width: 8,
          height: 6,
          left: [
            monitorFunction.metricInvocations({ statistic: 'Sum' }),
            monitorFunction.metricErrors({ statistic: 'Sum' }),
            monitorFunction.metricThrottles({ statistic: 'Sum' })
          ]
        })
      );

      // Monitor function duration
      lambdaWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'Monitor Function - Duration',
          width: 8,
          height: 6,
          left: [
            monitorFunction.metricDuration({ statistic: 'Average' }),
            monitorFunction.metricDuration({ statistic: 'Maximum' })
          ]
        })
      );

      // Monitor function concurrent executions
      lambdaWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'Monitor Function - Concurrent Executions',
          width: 8,
          height: 6,
          left: [
            new cloudwatch.Metric({
              namespace: 'AWS/Lambda',
              metricName: 'ConcurrentExecutions',
              dimensionsMap: { FunctionName: monitorFunction.functionName },
              statistic: 'Maximum'
            })
          ]
        })
      );
    }

    if (lambdaWidgets.length > 0) {
      this.dashboard.addWidgets(...lambdaWidgets);
    }

    // === QUERY FUNCTION ROW ===
    const queryWidgets: cloudwatch.IWidget[] = [];

    if (queryFunction) {
      // Query function invocations
      queryWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'Query Function - Invocations',
          width: 8,
          height: 6,
          left: [
            queryFunction.metricInvocations({ statistic: 'Sum' }),
            queryFunction.metricErrors({ statistic: 'Sum' }),
            queryFunction.metricThrottles({ statistic: 'Sum' })
          ]
        })
      );

      // Query function duration
      queryWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'Query Function - Duration',
          width: 8,
          height: 6,
          left: [
            queryFunction.metricDuration({ statistic: 'Average' }),
            queryFunction.metricDuration({ statistic: 'Maximum' }),
            queryFunction.metricDuration({ statistic: 'p99' })
          ]
        })
      );

      // Query function concurrent executions
      queryWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'Query Function - Concurrent Executions',
          width: 8,
          height: 6,
          left: [
            new cloudwatch.Metric({
              namespace: 'AWS/Lambda',
              metricName: 'ConcurrentExecutions',
              dimensionsMap: { FunctionName: queryFunction.functionName },
              statistic: 'Maximum'
            })
          ]
        })
      );
    }

    if (queryWidgets.length > 0) {
      this.dashboard.addWidgets(...queryWidgets);
    }

    // === API GATEWAY ROW ===
    const apiWidgets: cloudwatch.IWidget[] = [];

    if (api) {
      // API requests
      apiWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'API Gateway - Requests',
          width: 8,
          height: 6,
          left: [
            api.metricCount({ statistic: 'Sum' }),
            api.metricClientError({ statistic: 'Sum' }),
            api.metricServerError({ statistic: 'Sum' })
          ]
        })
      );

      // API latency
      apiWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'API Gateway - Latency',
          width: 8,
          height: 6,
          left: [
            api.metricLatency({ statistic: 'Average' }),
            api.metricLatency({ statistic: 'p99' }),
            api.metricIntegrationLatency({ statistic: 'Average' })
          ]
        })
      );

      // API error rates
      apiWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'API Gateway - Error Rates',
          width: 8,
          height: 6,
          left: [
            new cloudwatch.MathExpression({
              expression: '(m1 / m2) * 100',
              usingMetrics: {
                m1: api.metricClientError({ statistic: 'Sum' }),
                m2: api.metricCount({ statistic: 'Sum' })
              },
              label: '4xx Error Rate (%)'
            }),
            new cloudwatch.MathExpression({
              expression: '(m1 / m2) * 100',
              usingMetrics: {
                m1: api.metricServerError({ statistic: 'Sum' }),
                m2: api.metricCount({ statistic: 'Sum' })
              },
              label: '5xx Error Rate (%)'
            })
          ]
        })
      );
    }

    if (apiWidgets.length > 0) {
      this.dashboard.addWidgets(...apiWidgets);
    }

    // === CUSTOM METRICS ROW 1: Document Processing ===
    const docProcessingWidgets: cloudwatch.IWidget[] = [];

    // Documents processed over time
    docProcessingWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Documents Processed',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'DocumentsProcessed',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          }),
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'DocumentsUpdated',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    // Repositories checked
    docProcessingWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Repositories Checked',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'RepositoriesChecked',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    // Monitoring errors
    docProcessingWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Monitoring Errors',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'MonitoringErrors',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    this.dashboard.addWidgets(...docProcessingWidgets);

    // === CUSTOM METRICS ROW 2: Query Processing ===
    const queryProcessingWidgets: cloudwatch.IWidget[] = [];

    // Query latency
    queryProcessingWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Query Latency',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'QueryLatency',
            dimensionsMap: { Environment: environment },
            statistic: 'Average',
            unit: cloudwatch.Unit.SECONDS
          }),
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'QueryLatency',
            dimensionsMap: { Environment: environment },
            statistic: 'p99',
            unit: cloudwatch.Unit.SECONDS
          })
        ]
      })
    );

    // Documents retrieved per query
    queryProcessingWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Documents Retrieved per Query',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'DocumentsRetrieved',
            dimensionsMap: { Environment: environment },
            statistic: 'Average'
          })
        ]
      })
    );

    // Query errors
    queryProcessingWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Query Errors',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'QueryErrors',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    this.dashboard.addWidgets(...queryProcessingWidgets);

    // === CUSTOM METRICS ROW 3: Embeddings & LLM ===
    const embeddingsWidgets: cloudwatch.IWidget[] = [];

    // Embeddings generated
    embeddingsWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Embeddings Generated',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'EmbeddingsGenerated',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    // Embedding generation time
    embeddingsWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Embedding Generation Time',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'EmbeddingGenerationTime',
            dimensionsMap: { Environment: environment },
            statistic: 'Average',
            unit: cloudwatch.Unit.SECONDS
          }),
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'EmbeddingRetries',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    // LLM invocation time
    embeddingsWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'LLM Invocation Time',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'LLMInvocationTime',
            dimensionsMap: { Environment: environment },
            statistic: 'Average',
            unit: cloudwatch.Unit.SECONDS
          })
        ]
      })
    );

    this.dashboard.addWidgets(...embeddingsWidgets);

    // === CUSTOM METRICS ROW 4: Infrastructure ===
    const infraWidgets: cloudwatch.IWidget[] = [];

    // Vector store operations
    infraWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'Vector Store Operations',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'VectorStoreOperations',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ]
      })
    );

    // GitHub API calls and rate limits
    infraWidgets.push(
      new cloudwatch.GraphWidget({
        title: 'GitHub API Usage',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'GitHubAPICalls',
            dimensionsMap: { Environment: environment },
            statistic: 'Sum'
          })
        ],
        right: [
          new cloudwatch.Metric({
            namespace: 'Archon',
            metricName: 'GitHubRateLimitRemaining',
            dimensionsMap: { Environment: environment },
            statistic: 'Minimum'
          })
        ]
      })
    );

    // DynamoDB operations
    if (changeTrackerTable) {
      infraWidgets.push(
        new cloudwatch.GraphWidget({
          title: 'DynamoDB Operations',
          width: 8,
          height: 6,
          left: [
            new cloudwatch.Metric({
              namespace: 'Archon',
              metricName: 'DynamoDBOperations',
              dimensionsMap: { Environment: environment },
              statistic: 'Sum'
            }),
            new cloudwatch.Metric({
              namespace: 'Archon',
              metricName: 'DynamoDBThrottles',
              dimensionsMap: { Environment: environment },
              statistic: 'Sum'
            })
          ]
        })
      );
    }

    this.dashboard.addWidgets(...infraWidgets);

    // Apply tags
    cdk.Tags.of(this.dashboard).add('Environment', environment);
    cdk.Tags.of(this.dashboard).add('Project', 'Archon');
    cdk.Tags.of(this.dashboard).add('ManagedBy', 'CDK');
  }
}
