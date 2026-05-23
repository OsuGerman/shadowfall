/* global React, ASPECT_GLYPHS, ASPECT_LABEL, OrnamentCorner, OrnamentDivider, DropCap, FiligreeFrame, HexNode, ConstellationBackdrop */

// =========================================================================
// VELGRAD — Skill-Tree (Erinnerungs-Baum)
// Hexagonal web on aged parchment + constellations.
// =========================================================================

const SkillTreeScreen = ({ aspect = "valsa" }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;

  // Build node web procedurally — center "class start", arms outward
  const { nodes, edges } = useMemo(() => buildTree(), []);

  return (
    <div className="vg-page" style={{
      position: "relative", width: 1760, height: 1100,
      padding: 0, overflow: "hidden",
    }}>
      <ConstellationBackdrop density={130} opacity={0.45} seed={5}/>

      {/* HEADER */}
      <div style={{
        position: "absolute", top: 28, left: 56, right: 56,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.45em",
          color: "var(--vg-bronze-warm)", textTransform: "uppercase",
        }}>Codex&nbsp;Sartum &nbsp;·&nbsp; Liber&nbsp;Memoriae</div>
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 22, letterSpacing: "0.28em",
          color: "var(--vg-aspect-halo)", textShadow: "0 0 18px var(--vg-aspect)", fontWeight: 700,
        }}>D&nbsp;E&nbsp;R&nbsp; &nbsp;E&nbsp;R&nbsp;I&nbsp;N&nbsp;N&nbsp;E&nbsp;R&nbsp;U&nbsp;N&nbsp;G&nbsp;S&nbsp;-&nbsp;B&nbsp;A&nbsp;U&nbsp;M</div>
        <div style={{
          fontFamily: "var(--vg-mono)", fontSize: 11, letterSpacing: "0.18em",
          color: "var(--vg-bronze-light)",
        }}>FOL.&nbsp;CCXLVII&nbsp;·&nbsp;recto</div>
      </div>

      {/* LEFT PANEL — search + class info + paths spent */}
      <SidePanelLeft aspect={aspect}/>

      {/* CENTER — the tree */}
      <div style={{
        position: "absolute", left: 280, right: 360, top: 70, bottom: 60,
        overflow: "hidden",
      }}>
        <TreeCanvas nodes={nodes} edges={edges} aspect={aspect}/>
      </div>

      {/* RIGHT PANEL — hovered node detail + keystones */}
      <SidePanelRight/>

      {/* FOOTER */}
      <div style={{
        position: "absolute", bottom: 28, left: 56, right: 56,
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 12, color: "var(--vg-bronze-warm)", opacity: 0.85 }}>
          „Was du erinnerst, wirst du sein. Was du vergisst, fällt aus dir heraus."
        </div>
        <OrnamentDivider width={180} color="var(--vg-bronze-deep)"/>
        <div style={{ fontFamily: "var(--vg-mono)", fontSize: 10, letterSpacing: "0.2em", color: "var(--vg-bronze-warm)" }}>
          — der Fadengang folgt —
        </div>
      </div>
    </div>
  );
};

const { useMemo, useState } = React;

// -------------------------------------------------------------------------
// LEFT PANEL
// -------------------------------------------------------------------------

const SidePanelLeft = ({ aspect }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  return (
    <div style={{
      position: "absolute", left: 32, top: 70, bottom: 60, width: 232,
      display: "flex", flexDirection: "column", gap: 14,
    }}>
      {/* Class card */}
      <div style={{
        position: "relative", padding: 16,
        background: "linear-gradient(180deg, rgba(28,18,10,0.92), rgba(8,5,3,0.95))",
        border: "1px solid var(--vg-aspect)",
        boxShadow: "0 0 24px rgba(227,180,64,0.18)",
      }}>
        <div style={{ position: "absolute", top: -6, left: 14, padding: "2px 10px", background: "#0a0604", border: "1px solid var(--vg-aspect)", fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.3em", color: "var(--vg-aspect-halo)" }}>KLASSE</div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4 }}>
          <div style={{ color: "var(--vg-aspect-bright)" }}><A size={56}/></div>
          <div>
            <div style={{ fontFamily: "var(--vg-display)", fontSize: 16, fontWeight: 700, letterSpacing: "0.14em", color: "var(--vg-aspect-halo)" }}>
              FUNKEN-<br/>GEBORENE
            </div>
            <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 11, color: "var(--vg-vellum-mid)" }}>Valsa-berührt</div>
          </div>
        </div>
        <OrnamentDivider width={200} color="var(--vg-bronze)"/>
        <div style={{ marginTop: 6, fontFamily: "var(--vg-serif)", fontSize: 12, color: "var(--vg-vellum-mid)", lineHeight: 1.45, fontStyle: "italic" }}>
          „Sie sagten, ich solle nicht atmen. Ich brenne stattdessen."
        </div>
      </div>

      {/* Points budget */}
      <div style={{
        position: "relative", padding: 14,
        background: "rgba(10,7,3,0.55)", border: "1px solid var(--vg-bronze-deep)",
      }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 8 }}>ERINNERUNGEN</div>
        {[
          { l: "Vergeben", v: "63", c: "var(--vg-aspect-bright)" },
          { l: "Verbleibend", v: "4", c: "var(--vg-ghost-bright)" },
          { l: "Aschen-Punkte", v: "3", c: "var(--vg-blood-glow)" },
          { l: "Pakt-Punkte", v: "2", c: "#c9742a" },
        ].map(s => (
          <div key={s.l} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px dotted rgba(154,118,66,0.18)" }}>
            <span style={{ fontFamily: "var(--vg-serif)", fontSize: 12, color: "var(--vg-vellum-mid)" }}>{s.l}</span>
            <span style={{ fontFamily: "var(--vg-mono)", fontSize: 13, color: s.c }}>{s.v}</span>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{
        position: "relative", padding: "10px 12px",
        background: "rgba(10,7,3,0.55)", border: "1px solid var(--vg-bronze-deep)",
      }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 4 }}>SUCHEN · MURMELN</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontFamily: "var(--vg-display)", color: "var(--vg-aspect)", fontSize: 18 }}>⌖</span>
          <span style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 13, color: "var(--vg-vellum)" }}>
            "feuer&nbsp;ausbreiten"
            <span style={{ display: "inline-block", width: 1, height: 14, background: "var(--vg-aspect-bright)", verticalAlign: "middle", marginLeft: 4, animation: "vg-flicker 1200ms infinite" }}/>
          </span>
        </div>
        <div style={{ marginTop: 6, fontFamily: "var(--vg-mono)", fontSize: 10, color: "var(--vg-bronze-warm)", letterSpacing: "0.1em" }}>
          14 Treffer · 3 erreichbar
        </div>
      </div>

      {/* Active paths */}
      <div style={{
        position: "relative", padding: 14, flex: 1,
        background: "rgba(10,7,3,0.55)", border: "1px solid var(--vg-bronze-deep)",
        overflow: "hidden",
      }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 8 }}>BESCHRITTENE PFADE</div>
        {[
          { l: "Aschenherz",      v: "Notable · 12 Steine",  c: "var(--vg-blood-glow)" },
          { l: "Verbrannte Treue", v: "Notable · 9 Steine",  c: "var(--vg-aspect-bright)" },
          { l: "Spiegelblitz",     v: "Keystone",             c: "var(--vg-ghost-bright)" },
          { l: "Im-Nesh-Murmel",   v: "Pfad · 7 Steine",      c: "#864566" },
        ].map(p => (
          <div key={p.l} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px dotted rgba(154,118,66,0.18)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, background: p.c, transform: "rotate(45deg)", boxShadow: `0 0 6px ${p.c}` }}/>
              <span style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.15em", color: p.c, textTransform: "uppercase" }}>{p.l}</span>
            </div>
            <span style={{ fontFamily: "var(--vg-mono)", fontSize: 10, color: "var(--vg-bronze-warm)" }}>{p.v}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// -------------------------------------------------------------------------
// RIGHT PANEL — hovered node + keystone catalogue
// -------------------------------------------------------------------------

const SidePanelRight = () => (
  <div style={{
    position: "absolute", right: 32, top: 70, bottom: 60, width: 312,
    display: "flex", flexDirection: "column", gap: 14,
  }}>
    {/* Hovered node card */}
    <div style={{
      position: "relative", padding: 18,
      background: `
        radial-gradient(ellipse at 50% 0%, rgba(120,30,30,0.35), transparent 60%),
        linear-gradient(180deg, rgba(28,18,10,0.95), rgba(8,5,3,0.95))
      `,
      border: "1px solid var(--vg-blood-bright)",
      boxShadow: "0 0 26px rgba(184,30,30,0.28)",
    }}>
      {/* corner studs */}
      <span style={{ position:"absolute", top:-3, left:-3, width:7, height:7, background: "var(--vg-blood-bright)" }}/>
      <span style={{ position:"absolute", top:-3, right:-3, width:7, height:7, background: "var(--vg-blood-bright)" }}/>
      <span style={{ position:"absolute", bottom:-3, left:-3, width:7, height:7, background: "var(--vg-blood-bright)" }}/>
      <span style={{ position:"absolute", bottom:-3, right:-3, width:7, height:7, background: "var(--vg-blood-bright)" }}/>

      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.35em", color: "var(--vg-blood-glow)" }}>KEYSTONE · UNZERSTÖRBAR</div>
      <div style={{
        fontFamily: "var(--vg-display)", fontSize: 28, fontWeight: 800, letterSpacing: "0.14em",
        color: "var(--vg-vellum-pale)", textShadow: "0 0 16px rgba(184,30,30,0.6), 0 2px 0 #000",
        marginTop: 2, lineHeight: 1.1,
      }}>ASCHENHERZ</div>
      <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", color: "var(--vg-bronze-warm)", fontSize: 13, marginTop: 2 }}>
        Du brennst weiter, nachdem du fallen solltest.
      </div>

      <OrnamentDivider width={260} color="var(--vg-bronze)"/>

      <div style={{ marginTop: 6 }}>
        <StatBullet text="Du stirbst nicht bei 0 HP. Du brennst noch 4 Sekunden und kannst kämpfen."/>
        <StatBullet text="Während dieser Zeit ist dein Schaden +200%, deine Bewegung +30%."/>
        <StatBullet text="Nach den 4 Sekunden bist du tot."/>
        <StatBullet text="Diese Wirkung kann sich nicht wiederholen, bis du eine Stadt erreichst."/>
      </div>

      <div style={{
        marginTop: 12, padding: 10,
        borderTop: "1px solid var(--vg-bronze-deep)",
        background: "rgba(0,0,0,0.4)",
        fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 12,
        color: "var(--vg-vellum-mid)", lineHeight: 1.5, textAlign: "center",
      }}>
        „Valsa fiel. Aber sie ging weiter, vier Schritte. Vier ist heilig."
        <div style={{ marginTop: 4, fontStyle: "normal", fontSize: 10, color: "var(--vg-bronze-warm)", letterSpacing: "0.2em" }}>
          — Asch-Prophezeiung, Vers IX
        </div>
      </div>

      <div style={{
        marginTop: 12, display: "flex", gap: 8,
        fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.22em",
      }}>
        <span style={{ flex: 1, textAlign: "center", padding: "6px 8px", border: "1px solid var(--vg-aspect)", color: "var(--vg-aspect-halo)" }}>[KLICK] AKTIVIEREN</span>
        <span style={{ padding: "6px 12px", border: "1px solid var(--vg-bronze-deep)", color: "var(--vg-bronze-warm)" }}>[ALT] PFAD ZEIGEN</span>
      </div>
    </div>

    {/* Path requirements */}
    <div style={{
      position: "relative", padding: 14,
      background: "rgba(10,7,3,0.55)", border: "1px solid var(--vg-bronze-deep)",
    }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)", marginBottom: 6 }}>VORAUSSETZUNG</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <ReqLine label="Verbrannte Treue (Notable)" met/>
        <ReqLine label="9 Erinnerungen im Asch-Sektor" met/>
        <ReqLine label="Du hast Brassweir hinter dir gelassen" met/>
        <ReqLine label="Du hast keinen Pakt mit Im-Nesh"/>
      </div>
    </div>

    {/* Ascendancy */}
    <div style={{
      position: "relative", padding: 14, flex: 1,
      background: `
        radial-gradient(ellipse at 50% 0%, rgba(243,213,114,0.18), transparent 70%),
        rgba(10,7,3,0.6)
      `,
      border: "1px solid var(--vg-aspect-deep)",
    }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.32em", color: "var(--vg-aspect)", marginBottom: 8 }}>
        AUFSTIEGS-LINIE
      </div>
      {[
        { l: "Sturm-Weberin",     act: "Akt 3 · Aschenfelder", picked: true },
        { l: "Chronomantin",      act: "Akt 5 · Velharn" },
        { l: "Jüngerin Varashtas", act: "Endgame · Atlas" },
      ].map((a, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: i < 2 ? "1px dotted rgba(154,118,66,0.18)" : "none" }}>
          <span style={{ width: 14, height: 14, transform: "rotate(45deg)", background: a.picked ? "var(--vg-aspect-bright)" : "transparent", border: `1px solid ${a.picked ? "var(--vg-aspect)" : "var(--vg-bronze)"}`, boxShadow: a.picked ? "0 0 6px var(--vg-aspect-bright)" : "none" }}/>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.15em", color: a.picked ? "var(--vg-aspect-halo)" : "var(--vg-vellum-mid)" }}>{a.l.toUpperCase()}</div>
            <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 11, color: "var(--vg-bronze-warm)" }}>{a.act}</div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const StatBullet = ({ text }) => (
  <div style={{ display: "flex", gap: 8, padding: "3px 0" }}>
    <span style={{ color: "var(--vg-aspect-bright)", fontFamily: "var(--vg-display)", fontWeight: 800, fontSize: 12 }}>✦</span>
    <span style={{ fontFamily: "var(--vg-serif)", fontSize: 13, color: "var(--vg-vellum-warm)", lineHeight: 1.4 }}>{text}</span>
  </div>
);

const ReqLine = ({ label, met }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--vg-serif)", fontSize: 12, color: met ? "var(--vg-ghost-bright)" : "var(--vg-blood-glow)" }}>
    <span>{met ? "✓" : "✕"}</span>
    <span>{label}</span>
  </div>
);

// -------------------------------------------------------------------------
// TREE CANVAS — the hex web
// -------------------------------------------------------------------------

const TreeCanvas = ({ nodes, edges, aspect }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  return (
    <div style={{
      position: "relative", width: "100%", height: "100%",
      background: `
        radial-gradient(ellipse 60% 50% at 50% 50%, rgba(20,12,6,0.2), transparent 70%),
        repeating-linear-gradient(0deg, rgba(154,118,66,0.04) 0 1px, transparent 1px 60px),
        repeating-linear-gradient(60deg, rgba(154,118,66,0.04) 0 1px, transparent 1px 60px),
        repeating-linear-gradient(120deg, rgba(154,118,66,0.04) 0 1px, transparent 1px 60px)
      `,
    }}>
      {/* central aspect glyph BEHIND tree */}
      <div style={{
        position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)",
        color: "var(--vg-aspect-deep)", opacity: 0.18, pointerEvents: "none",
      }}>
        <A size={400}/>
      </div>

      <svg viewBox="0 0 1120 970" width="100%" height="100%" style={{ position: "absolute", inset: 0 }} preserveAspectRatio="xMidYMid meet">
        {/* edges */}
        {edges.map((e, i) => {
          const a = nodes[e[0]], b = nodes[e[1]];
          const allocated = a.allocated && b.allocated;
          const inPath = a.allocated || b.allocated;
          return (
            <line
              key={i}
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={allocated ? "var(--vg-aspect-bright)" : inPath ? "var(--vg-bronze)" : "var(--vg-bronze-deep)"}
              strokeWidth={allocated ? 3 : inPath ? 1.6 : 1.0}
              opacity={allocated ? 0.95 : inPath ? 0.75 : 0.55}
              style={{ filter: allocated ? "drop-shadow(0 0 3px var(--vg-aspect))" : "none" }}
            />
          );
        })}

        {/* ring etchings — three concentric circles */}
        {[150, 280, 420].map(r => (
          <circle key={r} cx="560" cy="485" r={r} fill="none" stroke="var(--vg-bronze-deep)" strokeWidth="0.6" strokeDasharray="2 6" opacity="0.5"/>
        ))}

        {/* nodes */}
        {nodes.map((n, i) => (
          <g key={i} transform={`translate(${n.x} ${n.y})`}>
            <HexBg
              size={n.size}
              allocated={n.allocated}
              available={n.available}
              notable={n.notable}
              keystone={n.keystone}
              kind={n.kind}
            />
            {(n.notable || n.keystone) && (
              <text x="0" y={n.size + 14} textAnchor="middle"
                    fontFamily="var(--vg-display)" fontSize={n.keystone ? "12" : "9"}
                    letterSpacing="0.15em"
                    fill={n.allocated ? "var(--vg-aspect-halo)" : "var(--vg-bronze-warm)"}
                    style={{ textTransform: "uppercase" }}>
                {n.label}
              </text>
            )}
          </g>
        ))}

        {/* CENTER class start */}
        <g transform="translate(560 485)">
          <polygon points={hexPts(40)} fill="rgba(184,30,30,0.25)" stroke="var(--vg-aspect)" strokeWidth="3"/>
          <polygon points={hexPts(34)} fill="rgba(28,18,10,0.85)" stroke="var(--vg-aspect-bright)" strokeWidth="1.5"/>
          <text x="0" y="6" textAnchor="middle" fontFamily="var(--vg-display)" fontWeight="800" fontSize="14" letterSpacing="0.12em" fill="var(--vg-aspect-halo)">FUNKE</text>
          <text x="0" y={60} textAnchor="middle" fontFamily="var(--vg-display)" fontWeight="700" fontSize="11" letterSpacing="0.3em" fill="var(--vg-aspect-halo)">— SAAT —</text>
        </g>

        {/* sector titles */}
        <SectorLabel x="220" y="200" label="ASCHE · WILLE"/>
        <SectorLabel x="900" y="200" label="STUNDE · ZEIT"/>
        <SectorLabel x="220" y="780" label="FADEN · BINDUNG"/>
        <SectorLabel x="900" y="780" label="WORT · SPRACHE"/>
      </svg>

      {/* Mouse-cursor crosshair */}
      <div style={{
        position: "absolute", left: "62%", top: "44%",
        width: 28, height: 28,
        border: "1px solid var(--vg-aspect-bright)",
        borderRadius: "50%",
        boxShadow: "0 0 18px var(--vg-aspect-bright)",
        pointerEvents: "none",
        transform: "translate(-50%,-50%)",
      }}>
        <div style={{ position: "absolute", left: -8, top: "50%", width: 6, height: 1, background: "var(--vg-aspect-bright)" }}/>
        <div style={{ position: "absolute", right: -8, top: "50%", width: 6, height: 1, background: "var(--vg-aspect-bright)" }}/>
        <div style={{ position: "absolute", top: -8, left: "50%", width: 1, height: 6, background: "var(--vg-aspect-bright)" }}/>
        <div style={{ position: "absolute", bottom: -8, left: "50%", width: 1, height: 6, background: "var(--vg-aspect-bright)" }}/>
      </div>

      {/* Mini-map (orientation) */}
      <div style={{
        position: "absolute", bottom: 18, right: 14, width: 160, height: 120,
        background: "rgba(8,5,3,0.85)", border: "1px solid var(--vg-bronze-deep)",
        padding: 6,
      }}>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 8, letterSpacing: "0.3em", color: "var(--vg-bronze-warm)", marginBottom: 2 }}>ÜBERSICHT</div>
        <div style={{ position: "relative", width: "100%", height: 80, background: "#050200", border: "1px solid var(--vg-bronze-deep)" }}>
          {/* dots */}
          {nodes.filter(n=>n.allocated).map((n,i)=>(
            <span key={i} style={{
              position:"absolute", left: `${(n.x/1120)*100}%`, top: `${(n.y/970)*100}%`,
              width: 2, height: 2, background: "var(--vg-aspect-bright)", borderRadius: "50%",
            }}/>
          ))}
          {/* viewport rect */}
          <div style={{ position:"absolute", left:"35%", top:"30%", width:"30%", height:"40%", border: "1px solid var(--vg-aspect-bright)" }}/>
        </div>
      </div>
    </div>
  );
};

const SectorLabel = ({ x, y, label }) => (
  <g transform={`translate(${x} ${y})`}>
    <text textAnchor="middle" fontFamily="var(--vg-display)" fontSize="11" letterSpacing="0.4em" fill="var(--vg-bronze)" opacity="0.85">{label}</text>
    <line x1="-70" y1="6" x2="-30" y2="6" stroke="var(--vg-bronze)" strokeWidth="0.6" opacity="0.6"/>
    <line x1="30" y1="6" x2="70" y2="6" stroke="var(--vg-bronze)" strokeWidth="0.6" opacity="0.6"/>
  </g>
);

const hexPts = (r) => [0,1,2,3,4,5].map(i => {
  const a = (Math.PI/3)*i - Math.PI/6;
  return `${r*Math.cos(a)},${r*Math.sin(a)}`;
}).join(" ");

const HexBg = ({ size, allocated, available, notable, keystone, kind }) => {
  const r = keystone ? 30 : notable ? 22 : 12;
  const fillColor = allocated
    ? "var(--vg-aspect)"
    : available ? "rgba(122,90,52,0.55)" : "rgba(20,14,8,0.85)";
  const strokeColor = allocated
    ? "var(--vg-aspect-bright)"
    : keystone ? "var(--vg-blood-bright)"
    : notable ? "var(--vg-gold-bright)"
    : "var(--vg-bronze-deep)";
  return (
    <g style={{ filter: allocated ? "drop-shadow(0 0 6px var(--vg-aspect-bright))" : keystone ? "drop-shadow(0 0 8px var(--vg-blood-glow))" : "none" }}>
      <polygon points={hexPts(r)} fill={fillColor} stroke={strokeColor} strokeWidth={keystone ? 2.5 : notable ? 1.8 : 1.2}/>
      {(notable || keystone) && <polygon points={hexPts(r-4)} fill="none" stroke={strokeColor} strokeWidth="0.6" opacity="0.5"/>}
      {/* kind glyph */}
      <NodeGlyph kind={kind} r={r} allocated={allocated}/>
    </g>
  );
};

const NodeGlyph = ({ kind, r, allocated }) => {
  const c = allocated ? "var(--vg-ink)" : "var(--vg-bronze-warm)";
  switch (kind) {
    case "fire":
      return <path d={`M 0 ${-r*0.5} Q ${-r*0.4} 0 ${-r*0.2} ${r*0.3} Q 0 ${r*0.45} ${r*0.2} ${r*0.3} Q ${r*0.4} 0 0 ${-r*0.5} Z`} fill={c} opacity="0.85"/>;
    case "cold":
      return <g stroke={c} strokeWidth="1.1"><line x1={0} y1={-r*0.55} x2={0} y2={r*0.55}/><line x1={-r*0.5} y1={0} x2={r*0.5} y2={0}/><line x1={-r*0.4} y1={-r*0.4} x2={r*0.4} y2={r*0.4}/><line x1={r*0.4} y1={-r*0.4} x2={-r*0.4} y2={r*0.4}/></g>;
    case "lightning":
      return <path d={`M ${-r*0.2} ${-r*0.55} L ${-r*0.4} ${r*0.05} L 0 ${r*0.05} L ${-r*0.1} ${r*0.55} L ${r*0.4} ${-r*0.1} L ${r*0.1} ${-r*0.1} Z`} fill={c}/>;
    case "life":
      return <path d={`M 0 ${r*0.55} C ${-r*0.45} ${r*0.25} ${-r*0.5} ${-r*0.2} ${-r*0.2} ${-r*0.4} C 0 ${-r*0.55} 0 ${-r*0.2} 0 ${-r*0.2} C 0 ${-r*0.2} 0 ${-r*0.55} ${r*0.2} ${-r*0.4} C ${r*0.5} ${-r*0.2} ${r*0.45} ${r*0.25} 0 ${r*0.55} Z`} fill={c}/>;
    case "spirit":
      return <g><circle r={r*0.35} fill={c}/><circle r={r*0.55} fill="none" stroke={c} strokeWidth="0.6" strokeDasharray="1 2"/></g>;
    case "mana":
      return <path d={`M 0 ${-r*0.55} C ${-r*0.4} ${-r*0.1} ${-r*0.45} ${r*0.3} 0 ${r*0.5} C ${r*0.45} ${r*0.3} ${r*0.4} ${-r*0.1} 0 ${-r*0.55} Z`} fill={c}/>;
    case "crit":
      return <path d={`M ${-r*0.5} 0 L ${r*0.5} ${-r*0.5} L 0 0 L ${r*0.5} ${r*0.5} Z`} fill={c}/>;
    case "armour":
      return <path d={`M 0 ${-r*0.55} L ${r*0.45} ${-r*0.25} L ${r*0.45} ${r*0.15} L 0 ${r*0.55} L ${-r*0.45} ${r*0.15} L ${-r*0.45} ${-r*0.25} Z`} fill="none" stroke={c} strokeWidth="1.2"/>;
    case "evade":
      return <g stroke={c} strokeWidth="1.2" fill="none"><path d={`M ${-r*0.4} ${r*0.4} L ${-r*0.1} ${-r*0.1} L ${r*0.2} ${r*0.1} L ${r*0.4} ${-r*0.4}`}/><circle r={r*0.55} fill="none" opacity="0.4"/></g>;
    default:
      return null;
  }
};

// -------------------------------------------------------------------------
// TREE BUILDER — produce nodes + edges layout
// -------------------------------------------------------------------------

function buildTree() {
  const cx = 560, cy = 485;
  const nodes = [];
  const edges = [];
  const ring = (count, r, opts={}) => {
    const start = nodes.length;
    for (let i = 0; i < count; i++) {
      const a = (i / count) * Math.PI * 2 - Math.PI/2 + (opts.offset || 0);
      nodes.push({
        x: cx + Math.cos(a) * r,
        y: cy + Math.sin(a) * r,
        kind: opts.kinds ? opts.kinds[i % opts.kinds.length] : opts.kind,
        size: 18,
        allocated: false, available: false, notable: false, keystone: false,
        ...opts.props,
      });
    }
    return start;
  };

  // Inner ring — 6 around start
  const inner = ring(6, 72, { kinds: ["fire","cold","lightning","life","mana","spirit"] });
  // Mid ring — 12
  const mid = ring(12, 150, { kinds: ["fire","fire","cold","cold","lightning","lightning","life","mana","spirit","crit","armour","evade"], offset: Math.PI/12 });
  // Outer ring — 18
  const outer = ring(18, 240, { kinds: ["fire","crit","cold","life","lightning","mana","spirit","armour","fire","cold","evade","lightning","life","crit","spirit","cold","fire","mana"] });
  // Distant ring — 18 sparse
  const distant = ring(18, 360, { kinds: ["crit","fire","life","cold","spirit","lightning","armour","mana","fire","evade","cold","life","spirit","crit","lightning","mana","armour","fire"] });

  // edges: connect inner ring to start (we draw start separately) — skip
  // Connect inner ring around
  for (let i = 0; i < 6; i++) edges.push([inner+i, inner+(i+1)%6]);
  // inner → mid (each inner connects to 2 mid)
  for (let i = 0; i < 6; i++) {
    edges.push([inner+i, mid + (i*2)]);
    edges.push([inner+i, mid + (i*2+1)]);
  }
  // mid ring around (sparse)
  for (let i = 0; i < 12; i++) edges.push([mid+i, mid+(i+1)%12]);
  // mid → outer
  for (let i = 0; i < 12; i++) {
    edges.push([mid+i, outer + Math.floor(i*1.5)]);
    edges.push([mid+i, outer + Math.floor(i*1.5+1)%18]);
  }
  // outer → distant
  for (let i = 0; i < 18; i++) {
    edges.push([outer+i, distant + i]);
  }

  // Notables — promote select nodes
  const promoteNotable = (idx, label) => { nodes[idx].notable = true; nodes[idx].size = 26; nodes[idx].label = label; };
  promoteNotable(mid + 0,  "FUNKEN-MUT");
  promoteNotable(mid + 4,  "EISWAND");
  promoteNotable(mid + 8,  "STILLER GEIST");
  promoteNotable(outer + 2, "AUSBREITUNG");
  promoteNotable(outer + 9, "FROST-HERZ");
  promoteNotable(outer + 14, "PAKT-MURMEL");
  promoteNotable(distant + 4, "SPIEGELBLITZ");
  promoteNotable(distant + 12, "ASCHEN-ATEM");

  // Keystones — even larger
  const keystone = (idx, label) => { nodes[idx].keystone = true; nodes[idx].notable = false; nodes[idx].size = 36; nodes[idx].label = label; };
  keystone(distant + 0, "ASCHENHERZ");
  keystone(distant + 9, "VERBRANNTE TREUE");
  keystone(distant + 16, "IM-NESHS WORT");

  // Allocated path (player's investment) — central start + a fire arm
  const allocate = (idx) => { nodes[idx].allocated = true; nodes[idx].available = true; };
  // inner around start: pick all 6 (early)
  for (let i = 0; i < 6; i++) allocate(inner+i);
  // mid: fire arm
  allocate(mid+0); allocate(mid+1); allocate(mid+11);
  // mid: lightning arm
  allocate(mid+4); allocate(mid+5);
  // outer: out into fire/lightning
  allocate(outer+0); allocate(outer+1); allocate(outer+2);
  allocate(outer+5); allocate(outer+6);
  // distant: aschenherz reached
  allocate(distant+0);
  allocate(distant+4);

  // Available (one ring out from allocated)
  const available = (idx) => { if (!nodes[idx].allocated) nodes[idx].available = true; };
  // adjacent to allocated outer & distant
  available(outer+3); available(outer+4); available(outer+7);
  available(distant+1); available(distant+3); available(distant+5);
  available(mid+2); available(mid+10); available(mid+6);

  return { nodes, edges };
}

window.SkillTreeScreen = SkillTreeScreen;
