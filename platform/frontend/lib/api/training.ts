/**
 * Training Job API
 */

import { apiClient } from "./client";

export interface TrainingJob {
  id: string;
  user_id: string;
  model_name: string;
  framework: string;
  dataset_s3_uri: string;
  config: Record<string, any> | null;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  message: string | null;
  checkpoint_s3_uri: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TrainingMetric {
  id: number;
  job_id: string;
  epoch: number;
  step: number | null;
  loss: number | null;
  accuracy: number | null;
  metrics: Record<string, any> | null;
  created_at: string;
}

export interface CreateTrainingJobRequest {
  user_id: string;
  model_name: string;
  framework: string;
  dataset_s3_uri: string;
  config?: Record<string, any>;
}

export const trainingApi = {
  async listJobs(params?: {
    user_id?: string;
    status_filter?: string;
    limit?: number;
    offset?: number;
  }): Promise<TrainingJob[]> {
    const response = await apiClient.get("/training/jobs", { params });
    return response.data;
  },

  async getJob(id: string): Promise<TrainingJob> {
    const response = await apiClient.get(`/training/jobs/${id}`);
    return response.data;
  },

  async createJob(data: CreateTrainingJobRequest): Promise<TrainingJob> {
    const response = await apiClient.post("/training/jobs", data);
    return response.data;
  },

  async cancelJob(id: string): Promise<void> {
    await apiClient.delete(`/training/jobs/${id}`);
  },

  async getMetrics(id: string, limit = 100): Promise<TrainingMetric[]> {
    const response = await apiClient.get(`/training/jobs/${id}/metrics`, {
      params: { limit },
    });
    return response.data;
  },
};
