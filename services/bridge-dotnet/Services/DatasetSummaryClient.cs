using System.Net.Http.Json;

namespace BridgeDotNet.Services;

public interface IDatasetSummaryClient
{
    Task<BridgeDatasetSummaryResponse> GetSummaryAsync(CancellationToken cancellationToken);
}

public sealed class DatasetSummaryClient(HttpClient httpClient) : IDatasetSummaryClient
{
    private const string DatasetsEndpointPath = "/datasets";

    public async Task<BridgeDatasetSummaryResponse> GetSummaryAsync(CancellationToken cancellationToken)
    {
        var datasetListResponse = await httpClient.GetFromJsonAsync<FastApiDatasetListResponse>(
            DatasetsEndpointPath,
            cancellationToken);

        if (datasetListResponse is null)
        {
            throw new HttpRequestException("ML API returned an empty dataset payload.");
        }

        var datasets = datasetListResponse.Datasets
            .Select(dataset => new BridgeDatasetSummaryItem(
                dataset.Id,
                dataset.Name,
                dataset.SequenceId,
                dataset.CameraName,
                dataset.FrameCount,
                dataset.CreatedAt))
            .ToArray();

        return new BridgeDatasetSummaryResponse(
            Source: httpClient.BaseAddress?.ToString().TrimEnd('/') ?? MlApiOptions.DefaultBaseUrl,
            DatasetCount: datasets.Length,
            TotalFrameCount: datasets.Sum(dataset => dataset.FrameCount),
            Datasets: datasets);
    }
}
