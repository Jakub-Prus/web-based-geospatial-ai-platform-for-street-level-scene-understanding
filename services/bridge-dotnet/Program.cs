using BridgeDotNet;
using BridgeDotNet.Services;
using Microsoft.Extensions.Options;

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<MlApiOptions>(
    builder.Configuration.GetSection(MlApiOptions.SectionName));
builder.Services
    .AddHttpClient<IDatasetSummaryClient, DatasetSummaryClient>()
    .ConfigureHttpClient((serviceProvider, httpClient) =>
    {
        var options = serviceProvider
            .GetRequiredService<IOptions<MlApiOptions>>()
            .Value;
        httpClient.BaseAddress = new Uri(options.BaseUrl, UriKind.Absolute);
    });

var app = builder.Build();

app.MapGet("/", () => Results.Ok(ServicePayloadFactory.Build()));
app.MapGet("/health", () => Results.Ok(ServicePayloadFactory.Build()));
app.MapGet("/bridge/health", () => Results.Ok(ServicePayloadFactory.Build()));
app.MapGet(
    "/bridge/datasets/summary",
    async (IDatasetSummaryClient datasetSummaryClient, CancellationToken cancellationToken) =>
    {
        try
        {
            var summary = await datasetSummaryClient.GetSummaryAsync(cancellationToken);
            return Results.Ok(summary);
        }
        catch (HttpRequestException exception)
        {
            return Results.Problem(
                title: "ML API unavailable",
                detail: exception.Message,
                statusCode: StatusCodes.Status503ServiceUnavailable);
        }
    });

app.Run();

public partial class Program;
