import React from "react";
import { exportPDF } from "../api";

const ExportButton = ({ rule, amcIndex, gmIndex }) => {
  return (
    <button onClick={() => exportPDF(rule, amcIndex, gmIndex)}>
      Download PDF
    </button>
  );
};
export default ExportButton;