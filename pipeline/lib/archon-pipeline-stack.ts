import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { AphexPipelineStack } from '@bdchatham/aphex-pipeline';
import { execSync } from 'child_process';

export interface ArchonPipelineStackProps extends cdk.StackProps {
  /**
   * Name of the shared EKS cluster running Arbiter Pipeline Infrastructure
   */
  readonly clusterName: string;

  /**
   * GitHub organization or user
   */
  readonly githubOwner: string;

  /**
   * GitHub repository name
   */
  readonly githubRepo: string;

  /**
   * Branch to monitor for changes
   * @default 'main'
   */
  readonly githubBranch?: string;

  /**
   * AWS Secrets Manager secret name containing GitHub token
   */
  readonly githubTokenSecretName: string;

  /**
   * Name for the Argo WorkflowTemplate resource
   * @default 'archon-agent-pipeline'
   */
  readonly workflowTemplateName?: string;

  /**
   * Name for the Argo Events EventSource resource
   * @default 'archon-agent-github'
   */
  readonly eventSourceName?: string;

  /**
   * Name for the Argo Events Sensor resource
   * @default 'archon-agent-sensor'
   */
  readonly sensorName?: string;

  /**
   * Base name for the S3 artifact bucket
   * @default 'archon-agent-artifacts'
   */
  readonly artifactBucketName?: string;

  /**
   * Number of days to retain artifacts in S3
   * @default 30
   */
  readonly artifactRetentionDays?: number;
}

/**
 * CDK Stack that creates deployment pipeline infrastructure for ArchonAgent
 * using the AphexPipeline construct.
 * 
 * This stack creates isolated pipeline resources on the shared Arbiter Pipeline
 * Infrastructure, including WorkflowTemplate, EventSource, Sensor, ServiceAccount,
 * IAM Role, and S3 bucket for artifacts.
 */
export class ArchonPipelineStack extends cdk.Stack {
  /**
   * The webhook URL for GitHub integration
   */
  public readonly webhookUrl: cdk.CfnOutput;

  /**
   * The name of the S3 bucket storing build artifacts
   */
  public readonly artifactBucketName: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: ArchonPipelineStackProps) {
    super(scope, id, props);

    // Apply default values
    const githubBranch = props.githubBranch ?? 'main';
    const workflowTemplateName = props.workflowTemplateName ?? 'archon-agent-pipeline';
    const eventSourceName = props.eventSourceName ?? 'archon-agent-github';
    const sensorName = props.sensorName ?? 'archon-agent-sensor';
    const artifactBucketName = props.artifactBucketName ?? 'archon-agent-artifacts';
    const artifactRetentionDays = props.artifactRetentionDays ?? 30;

    // Dynamically fetch the pipeline creator role ARN from CloudFormation exports
    // This is done at synthesis time because the construct validates ARN format
    let pipelineCreatorRoleArn: string;
    try {
      const result = execSync(
        `aws cloudformation list-exports --query 'Exports[?Name==\`ArbiterCluster-PipelineCreatorRoleArn\`].Value' --output text`,
        { encoding: 'utf-8' }
      ).trim();
      
      if (result && result !== '') {
        pipelineCreatorRoleArn = result;
        console.log(`Using PipelineCreatorRole: ${pipelineCreatorRoleArn}`);
      } else {
        // Fallback to constructed ARN if export not found
        pipelineCreatorRoleArn = `arn:aws:iam::${this.account}:role/arbiter-pipeline-creator`;
        console.warn(`PipelineCreatorRole export not found, using fallback: ${pipelineCreatorRoleArn}`);
      }
    } catch (error) {
      // Fallback if AWS CLI call fails
      pipelineCreatorRoleArn = `arn:aws:iam::${this.account}:role/arbiter-pipeline-creator`;
      console.warn(`Failed to fetch PipelineCreatorRole ARN, using fallback: ${pipelineCreatorRoleArn}`);
    }

    // Instantiate AphexPipelineStack construct with configuration
    // Use clusterExportPrefix to work with ArbiterCluster exports
    // Use pipelineCreatorRoleArn to safely access cluster resources
    // Both Argo Workflows and Argo Events are installed in the 'argo' namespace
    const pipeline = new AphexPipelineStack(this, 'AphexPipeline', {
      clusterName: props.clusterName,
      clusterExportPrefix: 'ArbiterCluster-',
      pipelineCreatorRoleArn: pipelineCreatorRoleArn,
      argoNamespace: 'argo',
      argoEventsNamespace: 'argo',
      githubOwner: props.githubOwner,
      githubRepo: props.githubRepo,
      githubBranch: githubBranch,
      githubTokenSecretName: props.githubTokenSecretName,
      workflowTemplateName: workflowTemplateName,
      eventSourceName: eventSourceName,
      sensorName: sensorName,
      artifactBucketName: artifactBucketName,
      artifactRetentionDays: artifactRetentionDays,
      configPath: '../aphex-config.yaml',
      // Container image configuration for convention-based ECR references
      containerImageAccount: this.account,
      containerImageRegion: this.region,
    });

    // Define stack outputs for webhook URL
    this.webhookUrl = new cdk.CfnOutput(this, 'WebhookUrl', {
      value: pipeline.argoEventsWebhookUrl,
      description: 'GitHub webhook URL for triggering pipeline executions',
      exportName: `${this.stackName}-WebhookUrl`,
    });

    // Define stack outputs for artifact bucket name
    this.artifactBucketName = new cdk.CfnOutput(this, 'ArtifactBucketName', {
      value: pipeline.artifactBucketName,
      description: 'S3 bucket name for storing build artifacts',
      exportName: `${this.stackName}-ArtifactBucketName`,
    });
  }
}
