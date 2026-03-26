const plannedSlices = [
  "Spatial dataset ingestion",
  "FastAPI inference endpoints",
  ".NET bridge integration",
  "Map and frame review UI",
];

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">Slice 1</p>
        <h1>Geospatial scene understanding platform</h1>
        <p className="lede">
          This frontend is intentionally minimal. It proves the React application
          scaffold exists and is ready for the dataset browsing and inference
          slices that follow.
        </p>
      </section>

      <section className="status-panel">
        <h2>Bootstrapped services</h2>
        <ul className="service-list">
          <li>Frontend: Vite + React + TypeScript</li>
          <li>ML service: FastAPI scaffold</li>
          <li>Bridge service: .NET 8 Web API scaffold</li>
          <li>Infrastructure: reserved for Docker and deployment assets</li>
        </ul>
      </section>

      <section className="roadmap-panel">
        <h2>Next slices</h2>
        <ol className="slice-list">
          {plannedSlices.map((slice) => (
            <li key={slice}>{slice}</li>
          ))}
        </ol>
      </section>
    </main>
  );
}
