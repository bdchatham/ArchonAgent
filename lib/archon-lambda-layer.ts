import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';

/**
 * Archon Lambda Layer Construct
 * 
 * Creates a Lambda layer with shared Python dependencies for Archon functions.
 * The layer includes langchain, opensearch-py, PyGithub, and other dependencies.
 * 
 * Usage:
 * 1. Build the layer: ./scripts/build-lambda-layer.sh
 * 2. Reference this construct in your Lambda functions
 * 
 * The layer is compatible with Python 3.11 runtime.
 */
export class ArchonLambdaLayer extends Construct {
  public readonly layer: lambda.LayerVersion;

  constructor(scope: Construct, id: string, environment: string) {
    super(scope, id);

    const layerPath = path.join(__dirname, '..', 'lambda-layer');

    this.layer = new lambda.LayerVersion(this, 'ArchonDependenciesLayer', {
      layerVersionName: `archon-dependencies-${environment}`,
      code: lambda.Code.fromAsset(layerPath),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Shared Python dependencies for Archon Lambda functions (langchain, opensearch-py, PyGithub)',
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // Apply tags
    cdk.Tags.of(this.layer).add('Environment', environment);
    cdk.Tags.of(this.layer).add('Project', 'Archon');
    cdk.Tags.of(this.layer).add('Component', 'LambdaLayer');
  }
}
