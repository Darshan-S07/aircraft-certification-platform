import React from "react";

// ✅ Render text with line breaks
const renderText = (text) => {
  return text.split("\n").map((line, i) => (
    <p key={i}>{line}</p>
  ));
};

// 🔥 Recursive renderer
const renderContent = (data) => {
  if (!data) return null;

  if (typeof data === "string") {
    return renderText(data); // ✅ FIXED MULTILINE
  }

  if (typeof data === "number") {
    return <p>{data}</p>;
  }

  if (Array.isArray(data)) {
    return data.map((item, i) => (
      <div key={i}>{renderContent(item)}</div>
    ));
  }

  if (typeof data === "object") {
    return Object.entries(data).map(([key, value]) => (
      <div key={key} style={{ marginLeft: "20px" }}>
        <b>({key})</b>
        {renderContent(value)}
      </div>
    ));
  }

  return <p>{String(data)}</p>;
};

const RuleViewer = ({ data }) => {
  if (!data) return <p>No data</p>;

  return (
    <div className="viewer">

      {/* 🔥 ALWAYS FIRST: CS */}
      {data.cs && (
        <div>
          <h2>CS</h2>
          <h3>{data.cs.title}</h3>
          {renderContent(data.cs.text)}
        </div>
      )}

      {/* 🔥 SECOND: SELECTED AMC ONLY */}
      {data.amc?.length > 0 && (
        <div>
          <h2>AMC</h2>
          {data.amc.map((a, i) => (
            <div key={i}>
              <h4>{a.title}</h4>
              {renderContent(a.text)}
            </div>
          ))}
        </div>
      )}

      {/* 🔥 THIRD: SELECTED GM ONLY */}
      {data.gm?.length > 0 && (
        <div>
          <h2>GM</h2>
          {data.gm.map((g, i) => (
            <div key={i}>
              <h4>{g.title}</h4>
              {renderContent(g.text)}
            </div>
          ))}
        </div>
      )}

    </div>
  );
};

export default RuleViewer;