#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ArchonInfrastructureStack } from '../lib/archon-infrastructure-stack';
import { ArchonKnowledgeBaseStack } from '../lib/archon-knowledge-base-stack';
import { ArchonAgentStack } from '../lib/archon-agent-stack';
import { ArchonMonitoringDashboard } from '../lib/archon-monitoring-dashboard';
import { ConfigLoader } from '../lib/config-loader';

/**
 * Archon Agent CDK Application
 * 
 * This application deploys the infrastructure for the Archon documentation agent.
 * It creates separate CloudFormation stacks for:
 * 1. Infrastructure (OpenSearch Serverless vector store)
 * 2. Knowledge Base (Document monitoring and ingestion)
 * 3. Agent (Query processing API)
 * 
 * Configuration is loaded from config/config.yaml
 */

const app = new cdk.App();

// Get environment from context or default to 'dev'
const environment = app.node.tryGetContext('environment') || 'dev';

// Get config path from context or use default
const configPath = app.node.tryGetContext('config') || './config/config.example.yaml';

// Load configuration
let config;
try {
  config = ConfigLoader.loadConfig(configPath);
  console.log(`✓ Configuration loaded successfully from ${configPath}`);
  console.log(`✓ Environment: ${environment}`);
  console.log(`✓ Repositories configured: ${config.repositories.length}`);
} catch (error) {
  console.error('✗ Failed to load configuration:', error);
  process.exit(1);
}

// Get AWS account and region from environment or CDK context
const account = process.env.CDK_DEFAULT_ACCOUNT || app.node.tryGetContext('account');
const region = process.env.CDK_DEFAULT_REGION || app.node.tryGetContext('region') || 'us-east-1';

const env = {
  account,
  region
};

// Create Infrastructure Stack (OpenSearch vector store)
const infraStack = new ArchonInfrastructureStack(app, `ArchonInfrastructure-${environment}`, {
  config,
  environment,
  env,
  description: 'Archon Agent - Infrastructure (OpenSearch Serverless)',
  tags: {
    Environment: environment,
    Project: 'Archon',
    Owner: 'ArchonTeam',
    CostCenter: 'Engineering'
  }
});

// Create Knowledge Base Stack (document monitoring and ingestion)
const knowledgeBaseStack = new ArchonKnowledgeBaseStack(app, `ArchonKnowledgeBase-${environment}`, {
  config,
  environment,
  infrastructure: infraStack,
  env,
  description: 'Archon Agent - Knowledge Base Ingestion and Maintenance',
  tags: {
    Environment: environment,
    Project: 'Archon',
    Owner: 'ArchonTeam',
    CostCenter: 'Engineering'
  }
});
knowledgeBaseStack.addDependency(infraStack);

// Create Agent Stack (query processing API)
const agentStack = new ArchonAgentStack(app, `ArchonAgent-${environment}`, {
  config,
  environment,
  infrastructure: infraStack,
  env,
  description: 'Archon Agent - Query Processing API',
  tags: {
    Environment: environment,
    Project: 'Archon',
    Owner: 'ArchonTeam',
    CostCenter: 'Engineering'
  }
});
agentStack.addDependency(infraStack);

// Create Monitoring Dashboard
const monitoringDashboard = new ArchonMonitoringDashboard(agentStack, 'MonitoringDashboard', {
  environment,
  monitorFunction: knowledgeBaseStack.monitorFunction,
  queryFunction: agentStack.queryFunction,
  api: agentStack.api,
  changeTrackerTable: knowledgeBaseStack.changeTrackerTable
});

app.synth();
