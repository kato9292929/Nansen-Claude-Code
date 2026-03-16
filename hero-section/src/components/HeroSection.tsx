"use client";

import { ChevronRight } from "lucide-react";
import { Button } from "./Button";
import { Navbar } from "./Navbar";

const VIDEO_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260309_042944_4a2205b7-b061-490a-852b-92d9e9955ce9.mp4";

const BRANDS = [
  "Vortex",
  "Nimbus",
  "Prysma",
  "Cirrus",
  "Kynder",
  "Halcyn",
];

// Duplicate for seamless loop
const BRAND_LIST = [...BRANDS, ...BRANDS];

export function HeroSection() {
  return (
    <section
      className="relative w-full min-h-screen flex flex-col overflow-hidden"
      style={{ backgroundColor: "hsl(260 87% 3%)" }}
    >
      {/* Background Video */}
      <video
        className="absolute inset-0 w-full h-full object-cover"
        src={VIDEO_URL}
        autoPlay
        loop
        muted
        playsInline
        aria-hidden="true"
      />

      {/* Overlay for legibility */}
      <div
        className="absolute inset-0"
        style={{ background: "rgba(2, 1, 8, 0.45)" }}
      />

      {/* Content stack */}
      <div className="relative z-10 flex flex-col flex-1">
        {/* Navbar */}
        <Navbar />

        {/* Hero body */}
        <div className="flex-1 flex flex-col items-center justify-center text-center px-4 pt-12 pb-4">
          {/* Announcement Badge */}
          <div className="liquid-glass rounded-full flex items-center gap-2 px-4 py-1.5 mb-8 w-fit">
            <span
              className="text-sm"
              style={{ color: "hsl(40 6% 95% / 0.85)" }}
            >
              Nova+ Launched!
            </span>
            <span
              className="flex items-center gap-0.5 rounded-full px-2 py-0.5 text-sm font-medium"
              style={{
                background: "rgba(255,255,255,0.05)",
                color: "hsl(121 95% 76%)",
              }}
            >
              Explore
              <ChevronRight className="w-3.5 h-3.5" />
            </span>
          </div>

          {/* Heading */}
          <h1
            className="text-4xl sm:text-6xl lg:text-7xl font-semibold tracking-tight leading-[1.05] max-w-5xl mb-6"
            style={{ color: "hsl(40 10% 96%)" }}
          >
            Accelerate Your Revenue Growth Now
          </h1>

          {/* Subheading */}
          <p
            className="text-lg max-w-md mb-10 opacity-80"
            style={{ color: "hsl(40 6% 82%)" }}
          >
            Drive your funnel forward with clever workflows, analytics, and
            seamless lead management.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <Button variant="hero">Start Free Right Now</Button>
            <Button variant="heroSecondary">Schedule a Consult</Button>
          </div>
        </div>

        {/* Social Proof Marquee */}
        <div className="relative z-10 w-full pb-10 pt-8">
          <div className="flex items-center gap-6 px-6 overflow-hidden">
            {/* Label */}
            <p
              className="text-sm whitespace-nowrap flex-shrink-0"
              style={{ color: "hsl(40 6% 95% / 0.5)" }}
            >
              Relied on by brands across the globe
            </p>

            {/* Marquee track */}
            <div className="overflow-hidden flex-1 min-w-0">
              <div className="flex gap-4 animate-marquee w-max">
                {BRAND_LIST.map((brand, i) => (
                  <div
                    key={`${brand}-${i}`}
                    className="flex items-center gap-2 flex-shrink-0"
                  >
                    {/* Brand icon */}
                    <div
                      className="liquid-glass w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      aria-hidden="true"
                    >
                      <span
                        className="text-sm font-semibold"
                        style={{ color: "hsl(40 6% 95%)" }}
                      >
                        {brand[0]}
                      </span>
                    </div>
                    <span
                      className="text-base font-semibold whitespace-nowrap"
                      style={{ color: "hsl(40 6% 95%)" }}
                    >
                      {brand}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
