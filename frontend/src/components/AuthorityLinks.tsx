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
      <h3 className="text-lg font-semibold mb-3">Authority Links</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {AUTHORITY_LINKS.map((item) => (
          <a
            key={item.name}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center justify-between p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#00d9ff]/40 transition"
          >
            <span className="flex items-center gap-2 text-xs font-medium text-white">
              <span aria-hidden>{item.icon}</span>
              <span>{item.name}</span>
            </span>
            <span className="text-xs text-[#888] group-hover:text-[#00d9ff] transition" aria-hidden>
              ↗
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}