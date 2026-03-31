import React, { useEffect, useState } from "react";
import Dropdown from "./components/Dropdown";
import RuleViewer from "./components/RuleViewer";
import ExportButton from "./components/ExportButton";
import { fetchRules, fetchRuleData,fetchSubparts } from "./api";
import "./index.css";


function App() {
  const [rules, setRules] = useState([]);
  const [selectedRule, setSelectedRule] = useState("");
  const [data, setData] = useState(null);
  const [selectedAMC, setSelectedAMC] = useState("");
  const [selectedGM, setSelectedGM] = useState("");
  const [subparts, setSubparts] = useState([]);
    const [selectedSubpart, setSelectedSubpart] = useState("");
  useEffect(() => {
    fetchSubparts().then(setSubparts);
  }, []);
  // Fetch rules list
  useEffect(() => {
    if (selectedSubpart) {
      fetchRules(selectedSubpart).then(setRules);
    }
  }, [selectedSubpart]);

  // Handle rule change
  const handleRuleChange = async (rule) => {
    setSelectedRule(rule);

    // 🔥 Reset AMC & GM when rule changes
    setSelectedAMC("");
    setSelectedGM("");

    const res = await fetchRuleData(rule);
    setData(res);
  };
  useEffect(() => {
    setSelectedRule("");
    setData(null);
  }, [selectedSubpart]);

  useEffect(() => {
  setSelectedRule("");
  setData(null);
  setSelectedAMC("");
  setSelectedGM("");
}, [selectedSubpart]);

  return (
    <div className="app">
      <h1>Certification Rule Viewer</h1>

      {/* Subpart (can upgrade later) */}
      <Dropdown
        label="Subpart"
        options={subparts.map(s => ({
          label: s,
          value: s
        }))}
        onChange={(value) => setSelectedSubpart(value)}
      />

      {/* CS Rule */}
      <Dropdown
        label="CS Rule"
        options={rules}
        onChange={handleRuleChange}
      />

      {/* AMC Dropdown */}
      {data?.amc?.length > 0 && (
        <Dropdown
          label="Select AMC"
          options={data.amc.map((a, i) => ({
            label: a.title,
            value: i
          }))}
          onChange={setSelectedAMC}
        />
      )}

      {/* GM Dropdown */}
      {data?.gm?.length > 0 && (
        <Dropdown
          label="Select GM"
          options={data.gm.map((g, i) => ({
            label: g.title,
            value: i
          }))}
          onChange={setSelectedGM}
        />
      )}

      {/* Export Button */}
      {selectedRule && <ExportButton
  rule={selectedRule}
  amcIndex={selectedAMC}
  gmIndex={selectedGM}
/>}

      {/* RULE VIEWER */}
      <RuleViewer
        data={{
          cs: data?.cs || null,
          amc:
            data && selectedAMC !== ""
              ? [data.amc?.[Number(selectedAMC)]]
              : [],
          gm:
            data && selectedGM !== ""
              ? [data.gm?.[Number(selectedGM)]]
              : []
        }}
      />
    </div>
  );
}

export default App;