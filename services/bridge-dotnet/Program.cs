var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => Results.Ok(ServicePayloadFactory.Build()));
app.MapGet("/health", () => Results.Ok(ServicePayloadFactory.Build()));

app.Run();

static class ServicePayloadFactory
{
    private const string ServiceName = "bridge-dotnet";
    private const string ServiceStatus = "ok";
    private const string ServiceVersion = "0.1.0";
    private const string FrameworkName = ".NET 8";

    public static object Build() =>
        new
        {
            service = ServiceName,
            status = ServiceStatus,
            version = ServiceVersion,
            framework = FrameworkName,
        };
}
