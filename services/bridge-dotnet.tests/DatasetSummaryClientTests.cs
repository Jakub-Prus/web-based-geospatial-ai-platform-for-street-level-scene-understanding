using System.Net;
using System.Net.Http;
using System.Text;
using BridgeDotNet.Services;
using Xunit;

namespace BridgeDotNet.Tests;

public sealed class DatasetSummaryClientTests
{
    [Fact]
    public async Task GetSummaryAsync_MapsFastApiDatasetsToBridgeSummary()
    {
        const string payload = """
            {
              "datasets": [
                {
                  "id": 1,
                  "name": "a2d2-subset",
                  "source_path": "C:/data/raw/a2d2-subset",
                  "sequence_id": "20190401_121727",
                  "camera_name": "front_right",
                  "frame_count": 20,
                  "created_at": "2019-04-01T10:51:51.596138Z"
                }
              ]
            }
            """;
        using var httpClient = new HttpClient(new StubHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(payload, Encoding.UTF8, "application/json"),
            }))
        {
            BaseAddress = new Uri("http://ml-fastapi:8000"),
        };
        var datasetSummaryClient = new DatasetSummaryClient(httpClient);

        var summary = await datasetSummaryClient.GetSummaryAsync(CancellationToken.None);

        Assert.Equal("http://ml-fastapi:8000", summary.Source);
        Assert.Equal(1, summary.DatasetCount);
        Assert.Equal(20, summary.TotalFrameCount);
        Assert.Single(summary.Datasets);
        Assert.Equal("a2d2-subset", summary.Datasets[0].Name);
        Assert.Equal("front_right", summary.Datasets[0].CameraName);
    }

    private sealed class StubHttpMessageHandler(
        Func<HttpRequestMessage, HttpResponseMessage> responseFactory) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken) =>
            Task.FromResult(responseFactory(request));
    }
}
