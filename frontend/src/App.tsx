const DEFAULT_FASTAPI_URL = "http://localhost:8000";
const DEFAULT_BRIDGE_URL = "http://localhost:8080";
const DEFAULT_OBJECT_STORAGE_CONSOLE_URL = "http://localhost:9001";

const plannedSlices = [
  "Spatial dataset ingestion",
  "PostGIS-backed frame persistence",
  "Map and frame review UI",
  "Detection and depth workflows",
];

const runtimeServices = [
  {
    href: "http://localhost:3000",
    label: "Frontend startup page",
    summary: "Static React application served from Docker.",
  },
  {
    href: import.meta.env.VITE_FASTAPI_BASE_URL ?? DEFAULT_FASTAPI_URL,
    label: "FastAPI root",
    summary: "Machine-learning API scaffold and health endpoint.",
  },
  {
    href: `${import.meta.env.VITE_FASTAPI_BASE_URL ?? DEFAULT_FASTAPI_URL}/health`,
    label: "FastAPI health",
    summary: "Simple runtime check for the Python service.",
  },
  {
    href: import.meta.env.VITE_BRIDGE_BASE_URL ?? DEFAULT_BRIDGE_URL,
    label: ".NET bridge root",
    summary: "Bridge API scaffold and runtime metadata.",
  },
  {
    href: `${import.meta.env.VITE_BRIDGE_BASE_URL ?? DEFAULT_BRIDGE_URL}/health`,
    label: ".NET bridge health",
    summary: "Simple runtime check for the .NET service.",
  },
  {
    href:
      import.meta.env.VITE_OBJECT_STORAGE_CONSOLE_URL ??
      DEFAULT_OBJECT_STORAGE_CONSOLE_URL,
    label: "Object storage console",
    summary: "MinIO console for local object-storage workflows.",
  },
];

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">Slice 2</p>
        <h1>Geospatial scene understanding platform</h1>
        <p className="lede">
          This startup page stays intentionally simple. It proves the Dockerized
          local runtime is up and shows where the empty stack is reachable before
          dataset ingestion and feature work begin.
        </p>
      </section>

      <section className="status-panel">
        <h2>Local runtime</h2>
        <ul className="service-list">
          {runtimeServices.map((service) => (
            <li key={service.label}>
              <a href={service.href} target="_blank" rel="noreferrer">
                {service.label}
              </a>
              : {service.summary}
            </li>
          ))}
        </ul>
      </section>

      <section className="roadmap-panel">
        <h2>Runtime notes</h2>
        <p className="lede">
          Docker Compose injects service URLs through Vite environment variables
          at build time. The backend service containers also receive placeholder
          database and object-storage settings so future slices can connect
          without changing the stack layout.
        </p>
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
