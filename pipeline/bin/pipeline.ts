#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ArchonPipelineStack } from '../lib/archon-pipeline-stack';

/**
 * Pipeline CDK Application Entry Point
 * 
 * This application creates the deployment pipeline infrastructure for ArchonAgent
 * using the AphexPipeline construct. The pipeline runs on shared Arbiter Pipeline
 * Infrastructure and deploys ArchonAgent stacks to configured environments.
 */

const app = new cdk.App();

// Get configuration from CDK context or environment variables
const account = process.env.CDK_DEFAULT_ACCOUNT || app.node.tryGetContext('account');
const region = process.env.CDK_DEFAULT_REGION || app.node.tryGetContext('region') || 'us-east-1';
const clusterName = app.node.tryGetContext('clusterName') || 'arbiter-pipeline-cluster';
const githubOwner = app.node.tryGetContext('githubOwner') || process.env.GITHUB_OWNER;
const githubRepo = app.node.tryGetContext('githubRepo') || process.env.GITHUB_REPO || 'archon-agent';
const githubBranch = app.node.tryGetContext('githubBranch') || process.env.GITHUB_BRANCH || 'main';
const githubTokenSecretName = app.node.tryGetContext('githubTokenSecretName') || process.env.GITHUB_TOKEN_SECRET_NAME || 'github-token';

// Validate required configuration
if (!githubOwner) {
  throw new Error('GitHub owner must be provided via context (githubOwner) or environment variable (GITHUB_OWNER)');
}

// Instantiate ArchonPipelineStack with environment configuration
const pipelineStack = new ArchonPipelineStack(app, 'ArchonAgentPipelineStack', {
  env: {
    account: account,
    region: region,
  },
  description: 'Deployment pipeline infrastructure for ArchonAgent application',
  clusterName: clusterName,
  githubOwner: githubOwner,
  githubRepo: githubRepo,
  githubBranch: githubBranch,
  githubTokenSecretName: githubTokenSecretName,
  workflowTemplateName: 'archon-agent-pipeline',
  eventSourceName: 'archon-agent-github',
  sensorName: 'archon-agent-sensor',
  artifactBucketName: 'archon-agent-artifacts',
  artifactRetentionDays: 30,
});

// Apply tags for resource management
cdk.Tags.of(pipelineStack).add('Project', 'ArchonAgent');
cdk.Tags.of(pipelineStack).add('ManagedBy', 'CDK');
cdk.Tags.of(pipelineStack).add('Environment', 'Pipeline');
cdk.Tags.of(pipelineStack).add('Component', 'DeploymentAutomation');

// Configure CDK app synthesis
app.synth();
