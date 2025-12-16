import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';

/**
 * Configuration structure matching config.yaml schema
 */
export interface ArchonConfig {
  version: string;
  repositories: RepositoryConfig[];
  infrastructure: InfrastructureConfig;
  models: ModelConfig;
}

export interface RepositoryConfig {
  url: string;
  branch: string;
  paths: string[];
}

export interface InfrastructureConfig {
  cron_schedule: string;
  lambda_memory: number;
  lambda_timeout: number;
  vector_db_dimensions: number;
}

export interface ModelConfig {
  embedding_model: string;
  llm_model: string;
  llm_temperature: number;
  max_tokens: number;
  retrieval_k: number;
}

/**
 * Utility class to load and validate CDK configuration from YAML files
 */
export class ConfigLoader {
  /**
   * Load configuration from a YAML file
   * @param configPath Path to the configuration file
   * @returns Parsed and validated configuration
   */
  static loadConfig(configPath: string): ArchonConfig {
    try {
      // Resolve the config path
      const resolvedPath = path.resolve(configPath);
      
      // Check if file exists
      if (!fs.existsSync(resolvedPath)) {
        throw new Error(`Configuration file not found: ${resolvedPath}`);
      }

      // Read and parse YAML
      const fileContents = fs.readFileSync(resolvedPath, 'utf8');
      const config = yaml.load(fileContents) as ArchonConfig;

      // Validate configuration
      this.validateConfig(config);

      return config;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to load configuration: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Validate the configuration structure and required fields
   * @param config Configuration to validate
   */
  private static validateConfig(config: ArchonConfig): void {
    // Validate version
    if (!config.version) {
      throw new Error('Configuration must include a version field');
    }

    // Validate repositories
    if (!config.repositories || !Array.isArray(config.repositories)) {
      throw new Error('Configuration must include a repositories array');
    }

    if (config.repositories.length === 0) {
      throw new Error('At least one repository must be configured');
    }

    config.repositories.forEach((repo, index) => {
      if (!repo.url) {
        throw new Error(`Repository at index ${index} missing required field: url`);
      }
      if (!repo.branch) {
        throw new Error(`Repository at index ${index} missing required field: branch`);
      }
      if (!repo.paths || !Array.isArray(repo.paths) || repo.paths.length === 0) {
        throw new Error(`Repository at index ${index} missing required field: paths`);
      }
    });

    // Validate infrastructure
    if (!config.infrastructure) {
      throw new Error('Configuration must include infrastructure section');
    }

    const infra = config.infrastructure;
    if (!infra.cron_schedule) {
      throw new Error('Infrastructure configuration missing required field: cron_schedule');
    }
    if (typeof infra.lambda_memory !== 'number' || infra.lambda_memory < 128 || infra.lambda_memory > 10240) {
      throw new Error('Infrastructure lambda_memory must be a number between 128 and 10240');
    }
    if (typeof infra.lambda_timeout !== 'number' || infra.lambda_timeout < 1 || infra.lambda_timeout > 900) {
      throw new Error('Infrastructure lambda_timeout must be a number between 1 and 900');
    }
    if (typeof infra.vector_db_dimensions !== 'number' || infra.vector_db_dimensions <= 0) {
      throw new Error('Infrastructure vector_db_dimensions must be a positive number');
    }

    // Validate models
    if (!config.models) {
      throw new Error('Configuration must include models section');
    }

    const models = config.models;
    if (!models.embedding_model) {
      throw new Error('Models configuration missing required field: embedding_model');
    }
    if (!models.llm_model) {
      throw new Error('Models configuration missing required field: llm_model');
    }
    if (typeof models.llm_temperature !== 'number' || models.llm_temperature < 0 || models.llm_temperature > 1) {
      throw new Error('Models llm_temperature must be a number between 0 and 1');
    }
    if (typeof models.max_tokens !== 'number' || models.max_tokens <= 0) {
      throw new Error('Models max_tokens must be a positive number');
    }
    if (typeof models.retrieval_k !== 'number' || models.retrieval_k <= 0) {
      throw new Error('Models retrieval_k must be a positive number');
    }
  }
}
