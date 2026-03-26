using System.Text.Json.Serialization;

namespace BridgeDotNet;

public sealed record FastApiDatasetListResponse(
    [property: JsonPropertyName("datasets")]
    IReadOnlyList<FastApiDatasetRecord> Datasets);

public sealed record FastApiDatasetRecord(
    [property: JsonPropertyName("id")]
    int Id,
    [property: JsonPropertyName("name")]
    string Name,
    [property: JsonPropertyName("source_path")]
    string SourcePath,
    [property: JsonPropertyName("sequence_id")]
    string SequenceId,
    [property: JsonPropertyName("camera_name")]
    string CameraName,
    [property: JsonPropertyName("frame_count")]
    int FrameCount,
    [property: JsonPropertyName("created_at")]
    string CreatedAt);

public sealed record BridgeDatasetSummaryResponse(
    string Source,
    int DatasetCount,
    int TotalFrameCount,
    IReadOnlyList<BridgeDatasetSummaryItem> Datasets);

public sealed record BridgeDatasetSummaryItem(
    int Id,
    string Name,
    string SequenceId,
    string CameraName,
    int FrameCount,
    string CreatedAt);
