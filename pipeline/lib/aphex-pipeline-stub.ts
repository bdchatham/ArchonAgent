import { Construct } from 'constructs';

/**
 * Configuration properties for AphexPipelineStack construct
 */
export interface AphexPipelineStackProps {
  readonly clusterName: string;
  readonly githubOwner: string;
  readonly githubRepo: string;
  readonly githubBranch: string;
  readonly githubTokenSecretName: string;
  readonly workflowTemplateName: string;
  readonly eventSourceName: string;
  readonly sensorName: string;
  readonly artifactBucketName: string;
  readonly artifactRetentionDays: number;
}

/**
 * Stub implementation of AphexPipelineStack construct
 * 
 * This is a placeholder for the actual @bdchatham/aphex-pipeline package.
 * In a real implementation, this would create:
 * - Argo WorkflowTemplate
 * - Argo Events EventSource
 * - Argo Events Sensor
 * - Kubernetes ServiceAccount
 * - IAM Role with IRSA
 * - S3 Bucket for artifacts
 */
export class AphexPipelineStack extends Construct {
  /**
   * The webhook URL for GitHub integration
   */
  public readonly webhookUrl: string;

  /**
   * The name of the S3 bucket storing build artifacts
   */
  public readonly artifactBucketName: string;

  constructor(scope: Construct, id: string, props: AphexPipelineStackProps) {
    super(scope, id);

    // Store configuration for validation
    this.validateProps(props);

    // Generate webhook URL based on cluster and event source
    this.webhookUrl = `https://${props.clusterName}.example.com/events/${props.eventSourceName}`;

    // Generate artifact bucket name with account and region
    const account = (scope as any).account || '123456789012';
    const region = (scope as any).region || 'us-east-1';
    this.artifactBucketName = `${props.artifactBucketName}-${account}-${region}`;
  }

  private validateProps(props: AphexPipelineStackProps): void {
    if (!props.clusterName) {
      throw new Error('clusterName is required');
    }
    if (!props.githubOwner) {
      throw new Error('githubOwner is required');
    }
    if (!props.githubRepo) {
      throw new Error('githubRepo is required');
    }
    if (!props.githubBranch) {
      throw new Error('githubBranch is required');
    }
    if (!props.githubTokenSecretName) {
      throw new Error('githubTokenSecretName is required');
    }
    if (!props.workflowTemplateName) {
      throw new Error('workflowTemplateName is required');
    }
    if (!props.eventSourceName) {
      throw new Error('eventSourceName is required');
    }
    if (!props.sensorName) {
      throw new Error('sensorName is required');
    }
    if (!props.artifactBucketName) {
      throw new Error('artifactBucketName is required');
    }
    if (props.artifactRetentionDays <= 0) {
      throw new Error('artifactRetentionDays must be positive');
    }
  }
}
