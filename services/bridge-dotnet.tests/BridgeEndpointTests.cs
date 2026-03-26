using System.Net;
using System.Net.Http.Json;
using BridgeDotNet.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

namespace BridgeDotNet.Tests;

public sealed class BridgeEndpointTests
{
    [Fact]
    public async Task BridgeHealthEndpoint_ReturnsBridgePayload()
    {
        await using var factory = new BridgeWebApplicationFactory(new StubDatasetSummaryClient(
            new BridgeDatasetSummaryResponse("http://ml-fastapi:8000", 0, 0, Array.Empty<BridgeDatasetSummaryItem>())));
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/bridge/health");

        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<Dictionary<string, string>>();
        Assert.NotNull(payload);
        Assert.Equal("bridge-dotnet", payload["service"]);
        Assert.Equal("ok", payload["status"]);
    }

    [Fact]
    public async Task DatasetSummaryEndpoint_ReturnsProxiedSummary()
    {
        var summary = new BridgeDatasetSummaryResponse(
            "http://ml-fastapi:8000",
            1,
            20,
            new[]
            {
                new BridgeDatasetSummaryItem(
                    1,
                    "a2d2-subset",
                    "20190401_121727",
                    "front_right",
                    20,
                    "2019-04-01T10:51:51.596138Z"),
            });
        await using var factory = new BridgeWebApplicationFactory(new StubDatasetSummaryClient(summary));
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/bridge/datasets/summary");

        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<BridgeDatasetSummaryResponse>();
        Assert.NotNull(payload);
        Assert.Equal(1, payload.DatasetCount);
        Assert.Equal(20, payload.TotalFrameCount);
        Assert.Single(payload.Datasets);
    }

    [Fact]
    public async Task DatasetSummaryEndpoint_ReturnsServiceUnavailableWhenMlApiFails()
    {
        await using var factory = new BridgeWebApplicationFactory(
            new FailingDatasetSummaryClient("Failed to reach ML API at http://ml-fastapi:8000/datasets."));
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/bridge/datasets/summary");

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        var payload = await response.Content.ReadFromJsonAsync<Dictionary<string, object>>();
        Assert.NotNull(payload);
    }

    private sealed class BridgeWebApplicationFactory(IDatasetSummaryClient datasetSummaryClient)
        : WebApplicationFactory<Program>
    {
        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<IDatasetSummaryClient>();
                services.AddSingleton(datasetSummaryClient);
            });
        }
    }

    private sealed class StubDatasetSummaryClient(BridgeDatasetSummaryResponse summary)
        : IDatasetSummaryClient
    {
        public Task<BridgeDatasetSummaryResponse> GetSummaryAsync(CancellationToken cancellationToken) =>
            Task.FromResult(summary);
    }

    private sealed class FailingDatasetSummaryClient(string message) : IDatasetSummaryClient
    {
        public Task<BridgeDatasetSummaryResponse> GetSummaryAsync(CancellationToken cancellationToken) =>
            throw new HttpRequestException(message);
    }
}
