export interface ModelInfo {
  id: string;
  name: string;
  version: string;
  crop: string;
  task: string;
  ready: boolean;
  supported_formats: string[];
}

export interface ApiStatus {
  online: boolean;
  models: ModelInfo[];
  message?: string;
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const endpoint = (path: string) => `${baseUrl}${path}`;

export async function getApiStatus(signal?: AbortSignal): Promise<ApiStatus> {
  try {
    const [healthResponse, modelsResponse] = await Promise.all([
      fetch(endpoint('/health/ready'), { signal }),
      fetch(endpoint('/api/v1/models'), { signal })
    ]);

    if (!healthResponse.ok || !modelsResponse.ok) {
      throw new Error('The plant-check service is not ready.');
    }

    const models = (await modelsResponse.json()) as ModelInfo[];
    return { online: true, models };
  } catch {
    return {
      online: false,
      models: [],
      message: 'Phytora cannot reach the plant-check service right now.'
    };
  }
}
