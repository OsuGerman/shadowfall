/* global React, ASPECT_GLYPHS, ASPECT_LABEL, OrnamentCorner, OrnamentDivider, DropCap, FiligreeFrame, ConstellationBackdrop */

// =========================================================================
// VELGRAD — Death-Screen
// Full-bleed memorial tablet — your name being un-written.
// =========================================================================

const DeathScreen = ({ aspect = "valsa" }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;

  return (
    <div style={{
      position: "relative", width: 1920, height: 1080, overflow: "hidden",
      background: `
        radial-gradient(ellipse at 50% 50%, #1a0606 0%, #0a0302 35%, #000 80%),
        #000
      `,
      color: "var(--vg-vellum)", fontFamily: "var(--vg-serif)",
    }}>
      {/* sparse cosmic dust */}
      <ConstellationBackdrop density={220} opacity={0.7} seed={9}/>

      {/* blood drip from top */}
      <BloodDrip/>

      {/* dim radial pulse */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: "radial-gradient(circle at 50% 55%, rgba(184,30,30,0.25) 0%, transparent 35%)",
        animation: "vg-breathe 5000ms ease-in-out infinite",
      }}/>

      {/* HUGE BACKGROUND GLYPH */}
      <div style={{
        position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)",
        color: "rgba(70, 20, 16, 0.5)", opacity: 0.6, pointerEvents: "none",
        animation: "vg-breathe 8000ms ease-in-out infinite",
      }}>
        <A size={1100}/>
      </div>

      {/* CRACK pattern across the screen */}
      <CrackOverlay/>

      {/* CONTENT */}
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        padding: "40px 0",
      }}>
        {/* Eyebrow */}
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 13, letterSpacing: "0.7em",
          color: "var(--vg-bronze)", textTransform: "uppercase", marginBottom: 22,
          textShadow: "0 0 12px rgba(0,0,0,0.85)",
        }}>— die welt vergißt einen namen —</div>

        {/* Ornament line */}
        <DeathOrnamentRail/>

        {/* MAIN TITLE */}
        <h1 style={{
          fontFamily: "var(--vg-display)", fontWeight: 900, fontSize: 168, lineHeight: 1,
          letterSpacing: "0.16em", margin: "26px 0 8px",
          color: "transparent",
          background: "linear-gradient(180deg, #f3d572 0%, #c89827 35%, #6a4d12 65%, #2a1a06 100%)",
          WebkitBackgroundClip: "text", backgroundClip: "text",
          filter: "drop-shadow(0 0 24px rgba(184,30,30,0.45)) drop-shadow(0 2px 0 rgba(0,0,0,0.9))",
          textShadow: "none",
          position: "relative",
        }}>
          <span style={{ position: "relative" }}>VERGANGEN</span>
        </h1>

        {/* Subtitle — fallen player name */}
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 28, letterSpacing: "0.3em",
          color: "var(--vg-vellum-warm)", marginTop: 14,
          textShadow: "0 2px 8px #000, 0 0 18px rgba(184,30,30,0.45)",
        }}>
          <span style={{ textDecoration: "line-through", textDecorationColor: "var(--vg-blood-bright)", textDecorationThickness: "2px" }}>
            HELÆN&nbsp;&nbsp;VAR-SKEIN
          </span>
        </div>
        <div style={{
          fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 17,
          color: "var(--vg-bronze-light)", marginTop: 10, letterSpacing: "0.1em",
          maxWidth: 760, textAlign: "center", lineHeight: 1.5,
        }}>
          „Asche-Tochter aus Brassweir, gefallen an der Aschwunde, im siebten Stunden-Spiegel der dunklen Stunde."
        </div>

        <div style={{ height: 36 }}/>

        <DeathOrnamentRail/>

        {/* === stats panel === */}
        <div style={{
          marginTop: 36,
          display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 56,
          width: 1320,
        }}>
          {/* LEFT: KILLER */}
          <KillerCard/>

          {/* CENTER: glyph + last-line */}
          <CenterPillar aspect={aspect}/>

          {/* RIGHT: LOSSES */}
          <LossesCard/>
        </div>

        {/* === choices === */}
        <div style={{
          marginTop: 50, display: "flex", gap: 26, alignItems: "stretch",
        }}>
          <ChoiceButton
            primary
            sigil="✚"
            keyHint="ENTER"
            title="STADT WIEDERFINDEN"
            sub="Verliere 12% Erinnerung · Brassweir"
            color="var(--vg-aspect-bright)"
          />
          <ChoiceButton
            sigil="◈"
            keyHint="C"
            title="CHECKPOINT"
            sub="Saatkind-Schrein · vor 04:12"
            color="var(--vg-ghost-bright)"
          />
          <ChoiceButton
            sigil="✥"
            keyHint="P"
            title="PAKT ERBITTEN"
            sub="Eine Bindung anbieten"
            color="#864566"
          />
          <ChoiceButton
            sigil="—"
            keyHint="ESC"
            title="VERGESSEN WERDEN"
            sub="Charakter beenden"
            color="var(--vg-bronze-warm)"
            grim
          />
        </div>
      </div>

      {/* edge vignette */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: "radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(0,0,0,0.85) 100%)",
      }}/>

      {/* footer credits */}
      <div style={{
        position: "absolute", bottom: 24, left: 0, right: 0, textAlign: "center",
        fontFamily: "var(--vg-mono)", fontSize: 10, letterSpacing: "0.45em",
        color: "var(--vg-bronze-deep)", textTransform: "uppercase",
      }}>
        velgrad &nbsp;·&nbsp; das aschene zeitalter &nbsp;·&nbsp; jahr 814 nach dem verrat
      </div>
    </div>
  );
};

// -------------------------------------------------------------------------
// Decorative pieces
// -------------------------------------------------------------------------

const DeathOrnamentRail = () => (
  <svg viewBox="0 0 920 28" width="920" height="28" fill="none">
    <line x1="0" y1="14" x2="360" y2="14" stroke="var(--vg-bronze)" strokeWidth="1" opacity="0.8"/>
    <line x1="560" y1="14" x2="920" y2="14" stroke="var(--vg-bronze)" strokeWidth="1" opacity="0.8"/>
    <line x1="80" y1="8" x2="320" y2="8" stroke="var(--vg-bronze-deep)" strokeWidth="0.6" opacity="0.6"/>
    <line x1="600" y1="8" x2="840" y2="8" stroke="var(--vg-bronze-deep)" strokeWidth="0.6" opacity="0.6"/>
    <line x1="80" y1="20" x2="320" y2="20" stroke="var(--vg-bronze-deep)" strokeWidth="0.6" opacity="0.6"/>
    <line x1="600" y1="20" x2="840" y2="20" stroke="var(--vg-bronze-deep)" strokeWidth="0.6" opacity="0.6"/>
    {/* center crest */}
    <g transform="translate(460 14)">
      <path d="M-30 0 L0 -10 L30 0 L0 10 Z" fill="none" stroke="var(--vg-bronze)" strokeWidth="1"/>
      <path d="M-18 0 L0 -6 L18 0 L0 6 Z" fill="var(--vg-bronze-deep)" stroke="var(--vg-bronze-warm)" strokeWidth="0.6"/>
      <circle r="3" fill="var(--vg-blood-bright)"/>
    </g>
    {/* flanking dots */}
    <circle cx="380" cy="14" r="2" fill="var(--vg-bronze-warm)"/>
    <circle cx="540" cy="14" r="2" fill="var(--vg-bronze-warm)"/>
  </svg>
);

const BloodDrip = () => (
  <svg viewBox="0 0 1920 1080" width="1920" height="1080" style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.85 }} preserveAspectRatio="none">
    <defs>
      <linearGradient id="dripGrad" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stopColor="#560c0c" stopOpacity="0"/>
        <stop offset="40%" stopColor="#8a1414" stopOpacity="0.5"/>
        <stop offset="100%" stopColor="#b81e1e" stopOpacity="0.85"/>
      </linearGradient>
    </defs>
    {/* heavy drips */}
    <path d="M280 0 L284 320 C284 340 296 348 300 360 C302 348 314 340 314 320 L318 0 Z" fill="url(#dripGrad)"/>
    <path d="M1500 0 L1504 450 C1504 470 1516 478 1520 490 C1522 478 1534 470 1534 450 L1538 0 Z" fill="url(#dripGrad)"/>
    {/* thin trickles */}
    <path d="M620 0 L622 180 L620 220 L618 180 Z" fill="url(#dripGrad)" opacity="0.7"/>
    <path d="M980 0 L982 90 L980 110 L978 90 Z" fill="url(#dripGrad)" opacity="0.7"/>
    <path d="M1180 0 L1182 260 L1180 290 L1178 260 Z" fill="url(#dripGrad)" opacity="0.7"/>
    <path d="M1740 0 L1742 130 L1740 150 L1738 130 Z" fill="url(#dripGrad)" opacity="0.7"/>
  </svg>
);

const CrackOverlay = () => (
  <svg viewBox="0 0 1920 1080" width="1920" height="1080" style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.45 }} preserveAspectRatio="none">
    <g stroke="#000" strokeWidth="1.2" fill="none">
      <path d="M0 540 L260 520 L420 560 L600 480 L740 540 L880 460 L1020 540 L1180 500 L1340 580 L1500 540 L1660 480 L1920 540"/>
      <path d="M260 520 L280 380 L300 240 M280 380 L200 360 L120 320"/>
      <path d="M740 540 L760 700 L790 820 M760 700 L660 740"/>
      <path d="M1180 500 L1200 300 L1220 180 M1200 300 L1080 280"/>
      <path d="M1500 540 L1480 740 L1460 880 M1480 740 L1380 760"/>
    </g>
  </svg>
);

const KillerCard = () => (
  <div style={{
    position: "relative",
    background: "linear-gradient(180deg, rgba(28,12,8,0.85), rgba(8,3,2,0.95))",
    border: "1px solid var(--vg-blood-dark)",
    boxShadow: "0 0 24px rgba(184,30,30,0.25), inset 0 0 30px rgba(0,0,0,0.7)",
    padding: 22,
  }}>
    {/* corners */}
    <div style={{ position: "absolute", top: -3, left: -3 }}><OrnamentCorner size={28} rotate={0} stroke="var(--vg-blood-bright)"/></div>
    <div style={{ position: "absolute", top: -3, right: -3 }}><OrnamentCorner size={28} rotate={90} stroke="var(--vg-blood-bright)"/></div>
    <div style={{ position: "absolute", bottom: -3, right: -3 }}><OrnamentCorner size={28} rotate={180} stroke="var(--vg-blood-bright)"/></div>
    <div style={{ position: "absolute", bottom: -3, left: -3 }}><OrnamentCorner size={28} rotate={270} stroke="var(--vg-blood-bright)"/></div>

    <div style={{ fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.42em", color: "var(--vg-blood-glow)" }}>VON DESSEN HAND</div>
    <div style={{
      fontFamily: "var(--vg-display)", fontWeight: 800, fontSize: 30, letterSpacing: "0.14em",
      color: "var(--vg-vellum-pale)", marginTop: 6, textShadow: "0 0 14px rgba(184,30,30,0.55)",
    }}>VOSSHEM,<br/>DER&nbsp;HOHLE&nbsp;BRAND</div>
    <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", color: "var(--vg-bronze-warm)", fontSize: 14, marginTop: 4 }}>
      Anomalie der Aschwunde · Akt III
    </div>

    <OrnamentDivider width={300} color="var(--vg-bronze-deep)"/>

    {/* killer silhouette */}
    <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 12 }}>
      <svg viewBox="0 0 80 96" width="80" height="96">
        <g fill="#0a0604" stroke="#1a0e08" strokeWidth="0.8">
          <path d="M40 8 C24 8 16 22 16 36 L16 56 L10 80 L26 92 L26 80 L20 70 L26 60 L26 40 L34 36 L40 40 L46 36 L54 40 L54 60 L60 70 L54 80 L54 92 L70 80 L64 56 L64 36 C64 22 56 8 40 8 Z"/>
          <circle cx="32" cy="34" r="2.5" fill="var(--vg-blood-glow)" opacity="0.9"/>
          <circle cx="48" cy="34" r="2.5" fill="var(--vg-blood-glow)" opacity="0.9"/>
          <circle cx="40" cy="22" r="2" fill="var(--vg-aspect-bright)" opacity="0.7"/>
        </g>
      </svg>
      <div style={{ flex: 1, fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 13, color: "var(--vg-vellum-mid)", lineHeight: 1.5 }}>
        „Du warst hier. Ich war hier. Wir werden beide nicht hier gewesen sein."
      </div>
    </div>

    <OrnamentDivider width={300} color="var(--vg-bronze-deep)"/>

    {/* killing blow stats */}
    <div style={{ marginTop: 8 }}>
      {[
        { l: "Letzter Schlag",    v: "Hohles Wort"        },
        { l: "Schaden",           v: "4 826 Chaos"        },
        { l: "Resistenz dabei",   v: "−12% Chaos"         },
        { l: "Lebenspunkte vor",  v: "2 640 / 2 640"      },
        { l: "Dauer im Kampf",    v: "00:42"              },
      ].map(r => (
        <div key={r.l} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px dotted rgba(154,118,66,0.15)" }}>
          <span style={{ fontFamily: "var(--vg-serif)", fontSize: 13, color: "var(--vg-vellum-mid)" }}>{r.l}</span>
          <span style={{ fontFamily: "var(--vg-mono)", fontSize: 13, color: "var(--vg-blood-glow)" }}>{r.v}</span>
        </div>
      ))}
    </div>
  </div>
);

const LossesCard = () => (
  <div style={{
    position: "relative",
    background: "linear-gradient(180deg, rgba(28,18,10,0.85), rgba(8,5,3,0.95))",
    border: "1px solid var(--vg-bronze)",
    boxShadow: "inset 0 0 30px rgba(0,0,0,0.7)",
    padding: 22,
  }}>
    <div style={{ position: "absolute", top: -3, left: -3 }}><OrnamentCorner size={28} rotate={0} stroke="var(--vg-bronze-warm)"/></div>
    <div style={{ position: "absolute", top: -3, right: -3 }}><OrnamentCorner size={28} rotate={90} stroke="var(--vg-bronze-warm)"/></div>
    <div style={{ position: "absolute", bottom: -3, right: -3 }}><OrnamentCorner size={28} rotate={180} stroke="var(--vg-bronze-warm)"/></div>
    <div style={{ position: "absolute", bottom: -3, left: -3 }}><OrnamentCorner size={28} rotate={270} stroke="var(--vg-bronze-warm)"/></div>

    <div style={{ fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.42em", color: "var(--vg-bronze-warm)" }}>WAS DIR ENTGEHT</div>
    <div style={{
      fontFamily: "var(--vg-display)", fontWeight: 800, fontSize: 30, letterSpacing: "0.14em",
      color: "var(--vg-vellum-pale)", marginTop: 6,
    }}>DAS&nbsp;VERGESSEN<br/>FORDERT</div>
    <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", color: "var(--vg-bronze-warm)", fontSize: 14, marginTop: 4 }}>
      Aschenes Zeitalter · Brassweir-Karavane
    </div>

    <OrnamentDivider width={300} color="var(--vg-bronze-deep)"/>

    {/* losses */}
    <div style={{ marginTop: 12 }}>
      {[
        { l: "Erinnerung",        v: "−86 420",    s: "(−12% Stufe)",  c: "var(--vg-aspect-bright)" },
        { l: "Asche-Gold",        v: "−2 480",     s: "",              c: "var(--vg-vellum)" },
        { l: "Pakt-Wachs",        v: "−2",         s: "von 8",          c: "var(--vg-blood-glow)" },
        { l: "Quest-Fortschritt", v: "behalten",   s: "Bruder Helst",  c: "var(--vg-ghost-bright)" },
        { l: "Karte verloren",    v: "Glas-Pass",  s: "(neu verschlossen)", c: "var(--vg-bronze-warm)" },
      ].map(r => (
        <div key={r.l} style={{ padding: "5px 0", borderBottom: "1px dotted rgba(154,118,66,0.15)" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontFamily: "var(--vg-serif)", fontSize: 13, color: "var(--vg-vellum-mid)" }}>{r.l}</span>
            <span style={{ fontFamily: "var(--vg-mono)", fontSize: 13, color: r.c }}>{r.v}</span>
          </div>
          {r.s && <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 11, color: "var(--vg-bronze-warm)", textAlign: "right" }}>{r.s}</div>}
        </div>
      ))}
    </div>

    {/* hollow-status warning */}
    <div style={{
      marginTop: 14, padding: 10,
      border: "1px dashed var(--vg-blood-dark)",
      background: "rgba(70,8,8,0.25)",
    }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.3em", color: "var(--vg-blood-glow)", marginBottom: 4 }}>WARNUNG</div>
      <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 12, color: "var(--vg-vellum-mid)", lineHeight: 1.5 }}>
        Drei weitere Tode in den Aschenfeldern, und du wirst <span style={{ color: "var(--vg-blood-glow)" }}>hohl</span> — kein Schatten, kein Spiegelbild.
      </div>
    </div>
  </div>
);

const CenterPillar = ({ aspect }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  const aspectLabel = ASPECT_LABEL[aspect];
  return (
    <div style={{
      width: 220,
      display: "flex", flexDirection: "column", alignItems: "center", gap: 14,
    }}>
      {/* big glyph in a bronze medallion */}
      <div style={{ position: "relative", width: 160, height: 160 }}>
        <svg viewBox="0 0 160 160" width="160" height="160" style={{ position: "absolute", inset: 0 }}>
          <circle cx="80" cy="80" r="74" fill="rgba(8,5,3,0.85)" stroke="var(--vg-bronze)" strokeWidth="3"/>
          <circle cx="80" cy="80" r="70" fill="none" stroke="var(--vg-bronze-warm)" strokeWidth="1"/>
          <circle cx="80" cy="80" r="62" fill="none" stroke="var(--vg-bronze-deep)" strokeWidth="0.6" strokeDasharray="2 3"/>
          {Array.from({ length: 24 }).map((_, i) => {
            const a = (i*Math.PI*2)/24;
            return <line key={i}
              x1={80+Math.cos(a)*66} y1={80+Math.sin(a)*66}
              x2={80+Math.cos(a)*72} y2={80+Math.sin(a)*72}
              stroke="var(--vg-bronze-warm)" strokeWidth={i%6===0 ? 1.6 : 0.6}
              opacity={i%6===0 ? 0.95 : 0.45}/>;
          })}
        </svg>
        <div style={{
          position: "absolute", inset: 0, display: "grid", placeItems: "center",
          color: "var(--vg-aspect-bright)",
          animation: "vg-glow-pulse 4500ms ease-in-out infinite",
        }}>
          <A size={88}/>
        </div>
      </div>

      <div style={{
        fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.4em",
        color: "var(--vg-bronze-warm)", textTransform: "uppercase",
      }}>Aspekt der {aspectLabel.domain}</div>

      {/* time of fall */}
      <div style={{
        marginTop: 8, padding: "8px 14px",
        border: "1px solid var(--vg-bronze-deep)",
        background: "rgba(10,7,3,0.5)",
        textAlign: "center",
      }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)" }}>
          STUNDE DES FALLS
        </div>
        <div style={{ fontFamily: "var(--vg-mono)", fontSize: 14, color: "var(--vg-vellum-warm)", marginTop: 4 }}>
          XIV·VII · 03:41
        </div>
        <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 11, color: "var(--vg-bronze-light)", marginTop: 2 }}>
          Spiegel-Stunde · zweiter Schatten
        </div>
      </div>

      {/* last spoken */}
      <div style={{ textAlign: "center", maxWidth: 220 }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 6 }}>LETZTES WORT</div>
        <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 14, color: "var(--vg-vellum)", lineHeight: 1.4 }}>
          „Ich bin nicht <span style={{ color: "var(--vg-blood-glow)" }}>—</span>"
        </div>
      </div>
    </div>
  );
};

const ChoiceButton = ({ primary, sigil, keyHint, title, sub, color, grim }) => (
  <button style={{
    position: "relative",
    minWidth: 240, padding: "18px 22px",
    background: primary
      ? `linear-gradient(180deg, rgba(80,50,16,0.85), rgba(28,18,10,0.95))`
      : `linear-gradient(180deg, rgba(20,14,8,0.85), rgba(8,5,3,0.95))`,
    border: `1px solid ${primary ? color : "var(--vg-bronze-deep)"}`,
    boxShadow: primary ? `0 0 24px ${color}33, inset 0 0 24px rgba(0,0,0,0.5)` : "inset 0 0 20px rgba(0,0,0,0.7)",
    color: "var(--vg-vellum)",
    textAlign: "left",
    cursor: "pointer",
    fontFamily: "var(--vg-serif)",
    opacity: grim ? 0.75 : 1,
  }}>
    {/* corners */}
    <span style={{ position:"absolute", top:-3, left:-3, width:6, height:6, background: primary ? color : "var(--vg-bronze)" }}/>
    <span style={{ position:"absolute", top:-3, right:-3, width:6, height:6, background: primary ? color : "var(--vg-bronze)" }}/>
    <span style={{ position:"absolute", bottom:-3, left:-3, width:6, height:6, background: primary ? color : "var(--vg-bronze)" }}/>
    <span style={{ position:"absolute", bottom:-3, right:-3, width:6, height:6, background: primary ? color : "var(--vg-bronze)" }}/>

    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
      <span style={{ fontFamily: "var(--vg-display)", fontSize: 18, color, opacity: 0.9 }}>{sigil}</span>
      <span style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.25em", color: "var(--vg-bronze-warm)", padding: "2px 6px", border: "1px solid var(--vg-bronze-deep)" }}>{keyHint}</span>
    </div>
    <div style={{ fontFamily: "var(--vg-display)", fontSize: 15, fontWeight: 700, letterSpacing: "0.18em", color: primary ? "var(--vg-aspect-halo)" : "var(--vg-vellum-pale)" }}>
      {title}
    </div>
    <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 11, color: "var(--vg-bronze-warm)", marginTop: 4 }}>
      {sub}
    </div>
  </button>
);

window.DeathScreen = DeathScreen;
