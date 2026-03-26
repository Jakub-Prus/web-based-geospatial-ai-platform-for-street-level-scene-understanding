namespace BridgeDotNet;

public sealed class MlApiOptions
{
    public const string SectionName = "MLApi";
    public const string DefaultBaseUrl = "http://localhost:8000";

    public string BaseUrl { get; init; } = DefaultBaseUrl;
}
