"use client";

import { ChevronDown, Crosshair } from "lucide-react";
import { Button } from "./Button";

const navItems = [
  { label: "Features", hasChevron: true },
  { label: "Solutions", hasChevron: false },
  { label: "Plans", hasChevron: false },
  { label: "Learning", hasChevron: true },
];

export function Navbar() {
  return (
    <nav className="w-full flex justify-center px-4 pt-6 relative z-20">
      <div className="liquid-glass rounded-3xl max-w-[850px] w-full flex items-center justify-between px-4 py-2.5">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{
              background:
                "linear-gradient(135deg, hsl(121 95% 76% / 0.3) 0%, hsl(260 87% 20% / 0.6) 100%)",
              boxShadow: "inset 0 1px 1px rgba(255,255,255,0.15)",
            }}
          >
            <Crosshair
              className="w-4 h-4"
              style={{ color: "hsl(121 95% 76%)" }}
            />
          </div>
          <span
            className="text-xl font-semibold tracking-wide"
            style={{ color: "hsl(40 6% 95%)" }}
          >
            APEX
          </span>
        </div>

        {/* Nav items */}
        <ul className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <li key={item.label}>
              <button
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-base transition-colors hover:bg-white/5"
                style={{ color: "hsl(40 6% 95% / 0.9)" }}
              >
                {item.label}
                {item.hasChevron && (
                  <ChevronDown className="w-3.5 h-3.5 opacity-60" />
                )}
              </button>
            </li>
          ))}
        </ul>

        {/* CTA */}
        <Button variant="navCta">Sign Up</Button>
      </div>
    </nav>
  );
}
