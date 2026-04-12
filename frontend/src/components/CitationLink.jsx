import React from "react";

export default function CitationLink({
  accession_no,
  source_section,
  source_page,
  filing_date,
  onOpen,
}) {
  const handleClick = () => {
    const detail = {
      accession_no,
      source_section,
      source_page,
      filing_date,
    };

    if (typeof onOpen === "function") {
      onOpen(detail);
      return;
    }

    window.dispatchEvent(
      new CustomEvent("edgarian:open-citation", {
        detail,
      }),
    );
  };

  return (
    <button className="citation-link" type="button" onClick={handleClick}>
      [open in viewer]
    </button>
  );
}
