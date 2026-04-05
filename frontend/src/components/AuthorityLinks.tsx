import React from "react";

type AuthorityLink = {
  name: string;
  url: string;
  icon: string;
};

const AUTHORITY_LINKS: AuthorityLink[] = [
  { name: "FDA", url: "https://www.fda.gov", icon: "🇺🇸" },
  { name: "EMA", url: "https://www.ema.europa.eu", icon: "🇪🇺" },
  { name: "ICH", url: "https://www.ich.org", icon: "🌐" },
  { name: "MHRA", url: "https://www.gov.uk/mhra", icon: "🇬🇧" },
  { name: "PMDA", url: "https://www.pmda.go.jp", icon: "🇯🇵" },
  { name: "CDSCO", url: "https://cdsco.gov.in", icon: "🇮🇳" },
  { name: "TGA", url: "https://www.tga.gov.au", icon: "🇦🇺" },
];

export default function AuthorityLinks() {
  return (
    <div className="card p-4 border border-white/10 fade-up">
      <h3 className="text-lg font-semibold mb-3 text-[#0b152b]">Authority Links</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {AUTHORITY_LINKS.map((item) => (
          <a
            key={item.name}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center justify-between p-2 rounded-lg bg-white hover:bg-[#f4fbff] border border-[#d8e2ef] hover:border-[#00d9ff]/60 transition"
          >
            <span className="flex items-center gap-2 text-xs font-semibold text-[#0b152b]">
              <span aria-hidden>{item.icon}</span>
              <span>{item.name}</span>
            </span>
            <span className="text-xs text-[#4b5b74] group-hover:text-[#00d9ff] transition" aria-hidden>
              ↗
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}