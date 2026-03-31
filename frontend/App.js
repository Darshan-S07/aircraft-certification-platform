import React, { useEffect, useState } from "react";
import Dropdown from "./components/Dropdown";
import RuleViewer from "./components/RuleViewer";
import ExportButton from "./components/ExportButton";
import { fetchRules, fetchRuleData } from "./api";
import "./styles.css";

function App() {
  const [rules, setRules] = useState([]);
  const [selectedRule, setSelectedRule] = useState("");
  const [data, setData] = useState(null);
  const [selectedAMC] = useState("");
  const [selectedGM] = useState("");

  useEffect(() => {
    fetchRules().then(setRules);
  }, []);

  const handleRuleChange = async (rule) => {
    setSelectedRule(rule);
    const res = await fetchRuleData(rule);
    setData(res);
  };

  return (
    <div className="app">
      <h1>Certification Rule Viewer</h1>

      {/* Subpart (Static for now) */}
      <Dropdown
        label="Subpart"
        options={[
          { label: "Subpart F", value: "F" },
          { label: "Subpart G", value: "G" }
        ]}
        onChange={() => {}}
      />

      {/* CS Rule */}
      <Dropdown
        label="CS Rule"
        options={rules}
        onChange={handleRuleChange}
      />

      {/* Export */}
      {selectedRule && <ExportButton rule={selectedRule} amcIndex={selectedAMC}
  gmIndex={selectedGM} />}

      {/* Viewer */}
      <RuleViewer data={data} />
    </div>
  );
}

export default App;