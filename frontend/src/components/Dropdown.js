import React from "react";

const Dropdown = ({ label, options, onChange }) => {
  return (
    <div className="dropdown">
      <label>{label}</label>
      <select onChange={(e) => onChange(e.target.value)}>
        <option value="">Select</option>
        {options.map((opt, i) => (
          <option key={i} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default Dropdown;