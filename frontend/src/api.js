const BASE_URL = "http://127.0.0.1:8000";

export const fetchRules = async (subpart) => {
  const url = subpart
    ? `http://localhost:8000/rules-list?subpart=${subpart}`
    : `http://localhost:8000/rules-list`;

  const res = await fetch(url);
  return res.json();
};

export const fetchRuleData = async (rule) => {
  const res = await fetch(`${BASE_URL}/rules/${rule}`);
  return res.json();
};

export const exportPDF = (rule, amcIndex, gmIndex) => {
  let url = `http://localhost:8000/export/${rule}?`;

  if (amcIndex !== "" && amcIndex !== undefined) {
    url += `amc=${amcIndex}`;
  }

  if (gmIndex !== "" && gmIndex !== undefined) {
    url += `${amcIndex !== "" ? "&" : "?"}gm=${gmIndex}`;
  }

  window.open(url, "_blank");
};

// const exportPDF = () => {
//   let url = `http://localhost:8000/export/${rule}?`;

//   if (amcIndex !== "") {
//     url += `amc=${amcIndex}&`;
//   }

//   if (gmIndex !== "") {
//     url += `gm=${gmIndex}`;
//   }

//   window.open(url);
// };

export const fetchSubparts = async () => {
  const res = await fetch(`${BASE_URL}/subparts`);
  return res.json();
};