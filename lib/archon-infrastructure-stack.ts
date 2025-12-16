import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';
import * as iam from 'aws-cdk-lib/aws-iam';
import { ArchonConfig } from './config-loader';

/**
 * Props for ArchonInfrastructureStack
 */
export interface ArchonInfrastructureStackProps extends cdk.StackProps {
  config: ArchonConfig;
  environment?: string;
}

/**
 * Infrastructure Stack for Archon Agent
 * 
 * This stack creates the core infrastructure for Archon:
 * - OpenSearch Serverless collection for vector storage
 * - IAM policies for Lambda access
 * 
 * Follows AWS Well-Architected Framework principles:
 * - Security: Encryption at rest, least-privilege IAM policies
 * - Reliability: Serverless architecture with automatic scaling
 * - Performance: Vector search optimized configuration
 * - Cost Optimization: Serverless pricing model
 * - Operational Excellence: CloudFormation outputs for cross-stack references
 */
export class ArchonInfrastructureStack extends cdk.Stack {
  public readonly collectionArn: string;
  public readonly collectionEndpoint: string;
  public readonly collectionName: string;
  public readonly dataAccessPolicyName: string;

  constructor(scope: Construct, id: string, props: ArchonInfrastructureStackProps) {
    super(scope, id, props);

    const environment = props.environment || 'dev';
    const config = props.config;

    // Generate unique collection name
    this.collectionName = `archon-vectors-${environment}`;

    // Create encryption policy for OpenSearch Serverless
    // Enables encryption at rest using AWS-managed keys
    const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'EncryptionPolicy', {
      name: `archon-encryption-${environment}`,
      type: 'encryption',
      policy: JSON.stringify({
        Rules: [
          {
            ResourceType: 'collection',
            Resource: [`collection/${this.collectionName}`]
          }
        ],
        AWSOwnedKey: true
      })
    });

    // Create network policy for OpenSearch Serverless
    // Allows public access (can be restricted to VPC if needed)
    const networkPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'NetworkPolicy', {
      name: `archon-network-${environment}`,
      type: 'network',
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: 'collection',
              Resource: [`collection/${this.collectionName}`]
            },
            {
              ResourceType: 'dashboard',
              Resource: [`collection/${this.collectionName}`]
            }
          ],
          AllowFromPublic: true
        }
      ])
    });

    // Create OpenSearch Serverless collection with vector search configuration
    const collection = new opensearchserverless.CfnCollection(this, 'VectorCollection', {
      name: this.collectionName,
      description: 'Vector database for Archon agent documentation storage',
      type: 'VECTORSEARCH',
      tags: [
        {
          key: 'Environment',
          value: environment
        },
        {
          key: 'Project',
          value: 'Archon'
        },
        {
          key: 'Owner',
          value: 'ArchonTeam'
        },
        {
          key: 'ManagedBy',
          value: 'CDK'
        }
      ]
    });

    // Ensure policies are created before collection
    collection.addDependency(encryptionPolicy);
    collection.addDependency(networkPolicy);

    // Store collection details
    this.collectionArn = collection.attrArn;
    this.collectionEndpoint = collection.attrCollectionEndpoint;

    // Create data access policy name for use in other stacks
    this.dataAccessPolicyName = `archon-data-access-${environment}`;

    // Create IAM policy for Lambda functions to access OpenSearch
    // This follows least-privilege principle by limiting to specific collection
    const opensearchAccessPolicy = new iam.ManagedPolicy(this, 'OpenSearchAccessPolicy', {
      managedPolicyName: `ArchonOpenSearchAccess-${environment}`,
      description: 'Allows Lambda functions to access Archon OpenSearch Serverless collection',
      statements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            'aoss:APIAccessAll'
          ],
          resources: [this.collectionArn]
        })
      ]
    });

    // CloudFormation outputs for cross-stack references
    new cdk.CfnOutput(this, 'CollectionArn', {
      value: this.collectionArn,
      description: 'ARN of the OpenSearch Serverless collection',
      exportName: `${this.stackName}-CollectionArn`
    });

    new cdk.CfnOutput(this, 'CollectionEndpoint', {
      value: this.collectionEndpoint,
      description: 'Endpoint URL of the OpenSearch Serverless collection',
      exportName: `${this.stackName}-CollectionEndpoint`
    });

    new cdk.CfnOutput(this, 'CollectionName', {
      value: this.collectionName,
      description: 'Name of the OpenSearch Serverless collection',
      exportName: `${this.stackName}-CollectionName`
    });

    new cdk.CfnOutput(this, 'OpenSearchAccessPolicyArn', {
      value: opensearchAccessPolicy.managedPolicyArn,
      description: 'ARN of the IAM policy for OpenSearch access',
      exportName: `${this.stackName}-OpenSearchAccessPolicyArn`
    });

    new cdk.CfnOutput(this, 'DataAccessPolicyName', {
      value: this.dataAccessPolicyName,
      description: 'Name of the data access policy for OpenSearch',
      exportName: `${this.stackName}-DataAccessPolicyName`
    });

    new cdk.CfnOutput(this, 'VectorDimensions', {
      value: config.infrastructure.vector_db_dimensions.toString(),
      description: 'Vector dimensions for embeddings',
      exportName: `${this.stackName}-VectorDimensions`
    });

    // Apply tags to all resources in the stack
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Project', 'Archon');
    cdk.Tags.of(this).add('Owner', 'ArchonTeam');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');
  }
}
