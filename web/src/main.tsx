import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { createDataSource, readSourceConfig } from "./data/source";
import "./styles.css";

function Root() {
  const [source, setSource] = useState(() => createDataSource());

  const switchToCached = () => {
    const url = new URL(window.location.href);
    url.searchParams.set("demo", "cached");
    window.history.replaceState(null, "", url);
    setSource(createDataSource({ ...readSourceConfig(), cached: true }));
  };

  return (
    <App
      key={source.kind}
      source={source}
      onUseCached={source.kind === "cached" ? undefined : switchToCached}
    />
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
