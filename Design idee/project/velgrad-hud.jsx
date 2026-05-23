/* global React, ASPECT_GLYPHS, ASPECT_LABEL, OrnamentCorner, OrnamentDivider, DropCap, FiligreeFrame, IconFireball, IconFrostbolt, IconArc, IconFlameWall, IconComet, IconHeraldAsh, IconPotion, SocketFrame, ConstellationBackdrop */

// =========================================================================
// VELGRAD — HUD (in-game)
// Diegetic occult tome chrome wrapping a PoE2-style action layout.
// =========================================================================

const HudScreen = ({ aspect = "valsa" }) => {
  const Aspect = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  const aspectLabel = ASPECT_LABEL[aspect];

  // === Resources ===
  const life = { cur: 1847, max: 2640 };
  const mana = { cur: 412, max: 720 };
  const spirit = { cur: 220, max: 320 };
  const lifePct = life.cur / life.max;
  const manaPct = mana.cur / mana.max;
  const spiritPct = spirit.cur / spirit.max;
  const xpPct = 0.62;

  const skills = [
    { id: 1, hot: "Q", name: "Feuerball",       cost: 18, kind: "fire",     gem: "Erinnerungsstein VI",  ready: true,  icon: IconFireball },
    { id: 2, hot: "W", name: "Frostsalve",      cost: 22, kind: "cold",     gem: "Erinnerungsstein IV",  ready: true,  icon: IconFrostbolt },
    { id: 3, hot: "E", name: "Flammenwand",     cost: 30, kind: "fire",     gem: "Erinnerungsstein V",   ready: true,  cd: 0.0, icon: IconFlameWall },
    { id: 4, hot: "R", name: "Komet",           cost: 75, kind: "cold",     gem: "Erinnerungsstein VIII",ready: false, cd: 0.42, icon: IconComet },
    { id: 5, hot: "1", name: "Blitzbogen",      cost: 14, kind: "lightning",gem: "Erinnerungsstein III", ready: true,  icon: IconArc },
    { id: 6, hot: "2", name: "Aschen-Herald",   cost: 60, kind: "spirit",   gem: "Pakt-Stein der Asche", reserved: 60, icon: IconHeraldAsh },
  ];

  return (
    <div style={{
      position: "relative", width: 1920, height: 1080, overflow: "hidden",
      fontFamily: "var(--vg-serif)", color: "var(--vg-vellum)",
      background: "#000",
    }}>
      {/* ============ GAME WORLD BACKDROP ============ */}
      <GameWorldBackdrop />

      {/* ============ TOP — Boss banner ============ */}
      <BossBanner />

      {/* ============ TOP-LEFT — Character cartouche ============ */}
      <CharCartouche aspect={aspect} />

      {/* ============ TOP-RIGHT — Minimap ============ */}
      <Minimap />

      {/* ============ LEFT EDGE — Buff/Debuff column ============ */}
      <BuffColumn />

      {/* ============ FLOATING COMBAT TEXT ============ */}
      <FloatingDamage />

      {/* ============ BOTTOM — Occult tome chrome ============ */}
      <BottomChrome
        life={life} mana={mana} spirit={spirit}
        lifePct={lifePct} manaPct={manaPct} spiritPct={spiritPct}
        xpPct={xpPct}
        skills={skills} aspect={aspect}
      />

      {/* corner vignette */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: "radial-gradient(ellipse at 50% 35%, transparent 30%, rgba(0,0,0,0.75) 90%)",
      }}/>
    </div>
  );
};

// -------------------------------------------------------------------------
// GAME WORLD — dark silhouette of a battle scene
// -------------------------------------------------------------------------

const GameWorldBackdrop = () => (
  <div style={{ position: "absolute", inset: 0 }}>
    {/* sky / sub-glow */}
    <div style={{
      position: "absolute", inset: 0,
      background: `
        radial-gradient(ellipse at 50% 90%, rgba(184,30,30,0.18) 0%, transparent 45%),
        radial-gradient(ellipse at 50% 30%, rgba(58,46,80,0.35) 0%, transparent 60%),
        linear-gradient(180deg, #050308 0%, #0a0b15 35%, #1a0a08 70%, #2a0b04 100%)
      `,
    }}/>
    {/* embers */}
    <ConstellationBackdrop density={140} opacity={0.7} seed={3} />

    {/* ASCHENFELDER scene — silhouettes */}
    <svg viewBox="0 0 1920 1080" width="1920" height="1080" style={{ position: "absolute", inset: 0 }} preserveAspectRatio="none">
      <defs>
        <linearGradient id="ground" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#1a0a05"/>
          <stop offset="100%" stopColor="#050200"/>
        </linearGradient>
        <radialGradient id="firePit" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f3d572" stopOpacity="0.95"/>
          <stop offset="35%" stopColor="#b81e1e" stopOpacity="0.7"/>
          <stop offset="100%" stopColor="#3a0808" stopOpacity="0"/>
        </radialGradient>
      </defs>

      {/* distant horizon mountains */}
      <path d="M0 560 L180 480 L320 520 L500 440 L720 500 L900 460 L1100 510 L1320 450 L1520 500 L1720 470 L1920 510 L1920 700 L0 700 Z" fill="#0c0608" opacity="0.85"/>
      <path d="M0 620 L200 580 L400 600 L640 550 L900 590 L1180 560 L1440 600 L1720 580 L1920 605 L1920 760 L0 760 Z" fill="#160807"/>

      {/* fire pit glow on ground */}
      <ellipse cx="1100" cy="780" rx="380" ry="80" fill="url(#firePit)" opacity="0.55"/>
      <ellipse cx="640" cy="800" rx="260" ry="60" fill="url(#firePit)" opacity="0.35"/>

      {/* broken pillars — Säulen-von-Helst */}
      <g fill="#0a0504" stroke="#1a0e08" strokeWidth="1.5">
        <path d="M140 380 L180 380 L188 720 L132 720 Z"/>
        <path d="M160 720 L160 380 M150 380 L170 380 L165 360 L155 360 Z"/>
        <path d="M1620 420 L1665 420 L1675 720 L1610 720 Z"/>
        <path d="M1640 720 L1640 420"/>
        <path d="M380 460 L408 460 L415 720 L373 720 Z"/>
        {/* fallen pillar */}
        <path d="M860 740 L1240 720 L1260 760 L840 760 Z"/>
      </g>

      {/* ground plane */}
      <rect x="0" y="700" width="1920" height="380" fill="url(#ground)"/>

      {/* charred trees */}
      <g stroke="#0c0604" strokeWidth="2.5" fill="none" opacity="0.85">
        <path d="M270 720 L268 600 M268 660 L260 640 M268 660 L276 645 M268 620 L260 605 M268 620 L278 612"/>
        <path d="M1480 720 L1483 580 M1483 650 L1474 632 M1483 650 L1492 638 M1483 600 L1474 588"/>
      </g>
    </svg>

    {/* player + enemy silhouettes (centered) */}
    <div style={{ position: "absolute", left: 0, right: 0, top: 540, display: "flex", justifyContent: "center", gap: 360 }}>
      {/* player — sorceress */}
      <div style={{ position: "relative", width: 120, height: 220 }}>
        <svg viewBox="0 0 120 220" width="120" height="220">
          <g fill="#0a0604" stroke="#1a0e08">
            {/* robe */}
            <path d="M60 30 C50 30 44 36 44 46 L44 70 L30 100 L36 200 L84 200 L90 100 L76 70 L76 46 C76 36 70 30 60 30 Z"/>
            <ellipse cx="60" cy="24" rx="10" ry="11" fill="#0a0604"/>
            {/* hood */}
            <path d="M44 30 C44 18 52 14 60 14 C68 14 76 18 76 30 L72 36 C68 28 60 26 60 26 C60 26 52 28 48 36 Z" fill="#08040a"/>
            {/* staff */}
            <line x1="20" y1="220" x2="44" y2="20" stroke="#3a2818" strokeWidth="3"/>
            <circle cx="44" cy="20" r="8" fill="#3a2818" stroke="#8a661a" strokeWidth="1"/>
            <circle cx="44" cy="20" r="4" fill="#e3b440" opacity="0.9"/>
          </g>
        </svg>
        {/* staff glow */}
        <div style={{ position: "absolute", left: 28, top: -6, width: 36, height: 36, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(243,213,114,0.85), transparent 70%)", filter: "blur(2px)",
          animation: "vg-breathe 3000ms ease-in-out infinite",
        }}/>
        {/* fireball trail */}
        <div style={{ position:"absolute", left: 70, top: 60, display:"flex", alignItems:"center", gap: 6 }}>
          <div style={{ width: 14, height: 4, background: "rgba(243,180,90,0.4)", borderRadius: 4 }}/>
          <div style={{ width: 20, height: 6, background: "rgba(243,180,90,0.6)", borderRadius: 4 }}/>
          <div style={{ width: 28, height: 18, borderRadius: "50%",
            background: "radial-gradient(circle, #fae9b0 10%, #e3b440 40%, #b81e1e 80%, transparent 100%)",
            boxShadow: "0 0 24px rgba(243,213,114,0.85)" }}/>
        </div>
      </div>

      {/* enemy — a hulking ash-thing */}
      <div style={{ position: "relative", width: 240, height: 280, marginTop: -40 }}>
        <svg viewBox="0 0 240 280" width="240" height="280">
          <g fill="#0a0604" stroke="#1a0e08">
            <path d="M120 18 C90 18 70 38 70 70 L70 110 L40 150 L40 220 L60 270 L100 270 L100 220 L80 200 L100 180 L100 140 L80 120 L100 130 L110 110 L140 110 L150 130 L168 120 L150 140 L150 180 L170 200 L150 220 L150 270 L190 270 L210 220 L210 150 L180 110 L180 70 C180 38 160 18 120 18 Z"/>
            <path d="M110 92 L80 84 L100 88 Z M150 88 L170 80 L155 92 Z" fill="#b81e1e" opacity="0.85"/>
            {/* third eye / ash */}
            <circle cx="120" cy="64" r="4" fill="#e3b440" opacity="0.9"/>
            {/* horns */}
            <path d="M80 30 L60 6 M158 30 L180 6" stroke="#1a0e08" strokeWidth="3" fill="none"/>
          </g>
        </svg>
      </div>
    </div>
  </div>
);

// -------------------------------------------------------------------------
// BOSS BANNER
// -------------------------------------------------------------------------

const BossBanner = () => (
  <div style={{
    position: "absolute", top: 36, left: "50%", transform: "translateX(-50%)",
    width: 760, textAlign: "center",
  }}>
    <div style={{
      fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.4em", color: "var(--vg-bronze-warm)",
      textTransform: "uppercase", marginBottom: 4,
    }}>— Anomalie der Aschwunde —</div>
    <div style={{
      fontFamily: "var(--vg-display)", fontSize: 34, letterSpacing: "0.22em", fontWeight: 700,
      color: "var(--vg-vellum-pale)", textShadow: "0 0 18px rgba(184,30,30,0.55), 0 2px 0 #000",
      marginBottom: 6,
    }}>VOSSHEM, DER HOHLE BRAND</div>
    <div style={{
      fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 14, color: "var(--vg-bronze-light)",
      marginBottom: 12, opacity: 0.85,
    }}>„Ich war ein Hauptmann. Ich vergaß meinen Namen, bevor sie mich vergaßen."</div>

    {/* boss hp bar */}
    <div style={{
      position: "relative", height: 22, border: "1px solid var(--vg-blood-dark)",
      background: "linear-gradient(180deg, #060000, #1a0606 70%, #000)",
      boxShadow: "0 0 0 1px rgba(0,0,0,0.6), inset 0 0 14px rgba(0,0,0,0.9), 0 0 24px rgba(140,20,20,0.35)",
    }}>
      <div style={{
        position: "absolute", inset: "1px auto 1px 1px", width: "62%",
        background: "linear-gradient(180deg, rgba(255,200,200,0.25) 0%, transparent 35%, rgba(0,0,0,0.55) 100%), linear-gradient(90deg, #560c0c, #b81e1e 65%, #d83838)",
        boxShadow: "inset 0 0 14px rgba(216,56,56,0.7)",
      }}/>
      <div style={{
        position: "absolute", left: "62%", top: 0, bottom: 0, width: 2,
        background: "var(--vg-gold-bright)", boxShadow: "0 0 6px var(--vg-gold-bright)",
        animation: "vg-flicker 2400ms infinite",
      }}/>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center",
        fontFamily: "var(--vg-mono)", fontSize: 12, color: "var(--vg-vellum-pale)", letterSpacing: "0.12em",
        textShadow: "0 1px 0 #000, 0 0 4px #000",
      }}>184&nbsp;320&nbsp;/&nbsp;297&nbsp;000</div>
    </div>
    <div style={{ marginTop: 6, display: "flex", justifyContent: "center", gap: 12, alignItems: "center" }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.3em", color: "var(--vg-bronze-warm)" }}>PHASE</div>
      <div style={{ display: "flex", gap: 4 }}>
        <div style={{ width: 14, height: 4, background: "var(--vg-vellum-mid)" }}/>
        <div style={{ width: 14, height: 4, background: "var(--vg-aspect-bright)", boxShadow: "0 0 6px var(--vg-aspect-bright)" }}/>
        <div style={{ width: 14, height: 4, background: "var(--vg-bronze-deep)" }}/>
        <div style={{ width: 14, height: 4, background: "var(--vg-bronze-deep)" }}/>
      </div>
      <div style={{ fontFamily: "var(--vg-mono)", fontSize: 11, color: "var(--vg-vellum-mid)", letterSpacing: "0.08em" }}>II / IV</div>
    </div>
  </div>
);

// -------------------------------------------------------------------------
// CHARACTER CARTOUCHE — top left
// -------------------------------------------------------------------------

const CharCartouche = ({ aspect }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  return (
    <div style={{
      position: "absolute", top: 28, left: 36, display: "flex", alignItems: "center", gap: 16,
    }}>
      {/* portrait */}
      <div style={{
        position: "relative", width: 82, height: 82,
        background: "radial-gradient(circle at 50% 38%, #2a1a10 0%, #0a0604 80%)",
        border: "1px solid var(--vg-bronze)",
        boxShadow: "inset 0 0 24px rgba(0,0,0,0.85), 0 0 0 2px #000, 0 0 0 3px var(--vg-bronze-deep)",
        clipPath: "polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%)",
      }}>
        {/* face silhouette */}
        <svg viewBox="0 0 82 82" width="82" height="82">
          <g fill="#0a0604" stroke="#3a2818" strokeWidth="0.8">
            <path d="M30 32 C30 26 35 22 41 22 C47 22 52 26 52 32 L52 40 L48 46 L34 46 L30 40 Z"/>
            <path d="M28 30 C28 18 36 14 41 14 C46 14 54 18 54 30 L50 26 C46 22 41 22 41 22 C41 22 36 22 32 26 Z" fill="#06030a"/>
            <ellipse cx="41" cy="56" rx="20" ry="6" fill="#160a06" opacity="0.65"/>
          </g>
        </svg>
        {/* eye glow */}
        <div style={{
          position: "absolute", left: 32, top: 28, width: 18, height: 6,
          background: "radial-gradient(ellipse, var(--vg-aspect-bright), transparent 70%)",
          filter: "blur(1px)", animation: "vg-breathe 3000ms ease-in-out infinite",
        }}/>
        {/* aspect mini-glyph badge */}
        <div style={{
          position: "absolute", right: -10, bottom: -6, width: 26, height: 26,
          display: "grid", placeItems: "center",
          background: "#0a0604", border: "1px solid var(--vg-aspect)",
          color: "var(--vg-aspect-bright)",
        }}>
          <A size={18}/>
        </div>
      </div>

      <div>
        <div style={{ fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.3em", color: "var(--vg-bronze-warm)" }}>STUFE 47 · FUNKENGEBORENE</div>
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 24, fontWeight: 700, letterSpacing: "0.16em",
          color: "var(--vg-vellum-pale)", textShadow: "0 0 10px rgba(0,0,0,0.85)", lineHeight: 1,
          marginTop: 2,
        }}>HELÆN VAR-SKEIN</div>
        <div style={{ fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 12, color: "var(--vg-vellum-mid)", marginTop: 2 }}>
          „Asche-Tochter aus Brassweir"
        </div>

        {/* XP rail */}
        <div style={{ marginTop: 8, width: 280, position: "relative" }}>
          <div style={{
            height: 4, background: "linear-gradient(180deg, #060300, #0a0604)",
            border: "1px solid var(--vg-bronze-deep)", boxShadow: "inset 0 1px 1px rgba(0,0,0,0.9)",
          }}>
            <div style={{ width: "62%", height: "100%",
              background: "linear-gradient(90deg, var(--vg-gold-deep), var(--vg-gold) 70%, var(--vg-gold-bright))",
              boxShadow: "0 0 6px var(--vg-gold-bright)",
            }}/>
          </div>
          <div style={{
            display: "flex", justifyContent: "space-between", marginTop: 3,
            fontFamily: "var(--vg-mono)", fontSize: 9, letterSpacing: "0.1em",
            color: "var(--vg-bronze-warm)",
          }}>
            <span>ERINNERUNG · 62%</span>
            <span>418 230 / 678 000</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// -------------------------------------------------------------------------
// MINIMAP — top right (parchment cartouche)
// -------------------------------------------------------------------------

const Minimap = () => (
  <div style={{
    position: "absolute", top: 28, right: 36, width: 280, height: 280,
  }}>
    <FiligreeFrame padding={6} corner={28}>
      <div style={{
        width: 256, height: 256, position: "relative",
        background: `
          radial-gradient(ellipse 110% 90% at 50% 50%, transparent 0%, rgba(0,0,0,0.6) 100%),
          radial-gradient(ellipse 30% 20% at 60% 38%, rgba(184,30,30,0.35), transparent 60%),
          linear-gradient(135deg, #1a120a, #0a0604)
        `,
        overflow: "hidden",
      }}>
        {/* paper-map graticule */}
        <svg viewBox="0 0 256 256" width="256" height="256" style={{ position: "absolute", inset: 0 }}>
          <defs>
            <pattern id="hatch" width="14" height="14" patternUnits="userSpaceOnUse">
              <path d="M0 14 L14 0" stroke="var(--vg-bronze-deep)" strokeWidth="0.4" opacity="0.5"/>
            </pattern>
          </defs>
          <rect width="256" height="256" fill="url(#hatch)"/>
          {/* roads / fog of war shapes */}
          <path d="M20 130 Q60 70 100 90 T180 60 T230 100" stroke="var(--vg-bronze-warm)" strokeWidth="1.2" fill="none" strokeDasharray="3 4" opacity="0.85"/>
          <path d="M40 220 Q90 200 120 170 T200 200" stroke="var(--vg-bronze-warm)" strokeWidth="1" fill="none" opacity="0.65"/>
          {/* explored area */}
          <path d="M70 100 Q120 70 170 110 Q200 150 160 200 Q100 220 60 180 Q40 140 70 100 Z" fill="rgba(60,42,22,0.45)" stroke="var(--vg-bronze)" strokeWidth="0.6" opacity="0.7"/>
          {/* points of interest */}
          <g fontFamily="var(--vg-display)" fontSize="7" fill="var(--vg-vellum-mid)" letterSpacing="1">
            <text x="42" y="62">SÄULEN&nbsp;v.&nbsp;HELST</text>
            <text x="170" y="46">ASCHWUNDE</text>
            <text x="92" y="222">KARAWANENLAGER</text>
          </g>
          {/* boss marker */}
          <g transform="translate(165 105)">
            <polygon points="0,-7 6,5 -6,5" fill="var(--vg-blood-bright)" stroke="#000" strokeWidth="0.5"/>
          </g>
          {/* npc markers */}
          <circle cx="52" cy="206" r="3" fill="var(--vg-ghost-bright)" stroke="#000" strokeWidth="0.5"/>
          <circle cx="200" cy="178" r="3" fill="var(--vg-gold-bright)" stroke="#000" strokeWidth="0.5"/>
        </svg>
        {/* player marker — center */}
        <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)" }}>
          <div style={{ width: 16, height: 16, position: "relative" }}>
            <div style={{ position: "absolute", inset: 0, border: "2px solid var(--vg-aspect-bright)", transform: "rotate(45deg)", boxShadow: "0 0 12px var(--vg-aspect-bright)"}}/>
            <div style={{ position: "absolute", inset: 4, background: "var(--vg-aspect)", transform: "rotate(45deg)" }}/>
          </div>
        </div>
        {/* compass NESW */}
        <div style={{ position: "absolute", top: 6, left: "50%", transform: "translateX(-50%)", fontFamily: "var(--vg-display)", fontSize: 10, color: "var(--vg-bronze-light)", letterSpacing: "0.2em" }}>N</div>
        <div style={{ position: "absolute", bottom: 6, left: "50%", transform: "translateX(-50%)", fontFamily: "var(--vg-display)", fontSize: 10, color: "var(--vg-bronze-warm)", letterSpacing: "0.2em", opacity: 0.5 }}>S</div>
      </div>
    </FiligreeFrame>
    {/* location title */}
    <div style={{
      position: "absolute", top: -16, left: 0, right: 0, textAlign: "center",
      fontFamily: "var(--vg-display)", fontSize: 11, letterSpacing: "0.32em", color: "var(--vg-bronze-warm)",
      textTransform: "uppercase",
    }}>
      <span style={{ background: "linear-gradient(180deg, #0a0604, #1a0e08)", padding: "2px 14px", border: "1px solid var(--vg-bronze-deep)" }}>
        Aschenfelder · Glas-Pass
      </span>
    </div>
    <div style={{
      position: "absolute", bottom: -22, right: 0,
      fontFamily: "var(--vg-mono)", fontSize: 10, letterSpacing: "0.1em",
      color: "var(--vg-bronze-light)",
    }}>
      52°&nbsp;14′&nbsp;N · 09°&nbsp;47′&nbsp;O
    </div>
  </div>
);

// -------------------------------------------------------------------------
// BUFF / DEBUFF column
// -------------------------------------------------------------------------

const BuffColumn = () => {
  const buffs = [
    { name: "Aschen-Herald",    type: "buff",  remain: "Persistent", color: "var(--vg-gold-bright)", icon: <IconHeraldAsh size={28}/> },
    { name: "Hast (Funke)",     type: "buff",  remain: "08.4s",      color: "var(--vg-aspect-bright)", icon: "↟" },
    { name: "Verbrennen",       type: "debuff",remain: "04.1s",      color: "var(--vg-blood-glow)",    icon: "≈" },
    { name: "Gebrochener Eid",  type: "curse", remain: "—",          color: "#864566",                 icon: "✥" },
  ];
  return (
    <div style={{
      position: "absolute", top: 230, left: 36,
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.35em", color: "var(--vg-bronze-warm)", marginBottom: 4 }}>RESONANZEN</div>
      {buffs.map((b, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <div style={{
            position: "relative",
            width: 42, height: 42,
            background: "linear-gradient(160deg, #0a0604, #1a0e08)",
            border: `1px solid ${b.color}`,
            display: "grid", placeItems: "center",
            color: b.color, fontSize: 22,
            boxShadow: `0 0 8px ${b.color}66, inset 0 0 8px rgba(0,0,0,0.8)`,
          }}>
            {b.icon}
            {/* corner studs */}
            {[[-2,-2],[-2,40],[40,-2],[40,40]].map(([x,y],k)=>(
              <span key={k} style={{ position:"absolute", left:x, top:y, width:4, height:4, background: b.color, opacity: 0.8 }}/>
            ))}
          </div>
          <div>
            <div style={{ fontFamily: "var(--vg-display)", fontSize: 10, letterSpacing: "0.2em", color: "var(--vg-vellum-warm)", textTransform: "uppercase" }}>{b.name}</div>
            <div style={{ fontFamily: "var(--vg-mono)", fontSize: 10, color: b.color }}>{b.remain}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

// -------------------------------------------------------------------------
// FLOATING COMBAT TEXT — staged crits and procs
// -------------------------------------------------------------------------

const FloatingDamage = () => (
  <>
    <div style={{
      position: "absolute", left: "62%", top: 320,
      fontFamily: "var(--vg-display)", fontSize: 42, fontWeight: 800,
      color: "var(--vg-gold-leaf)", letterSpacing: "0.05em",
      textShadow: "0 0 16px rgba(243,213,114,0.85), 0 2px 0 #000",
      transform: "rotate(-3deg)",
    }}>4&nbsp;218 <span style={{ fontSize: 18, color: "var(--vg-blood-glow)", verticalAlign: "super" }}>·CRIT·</span></div>
    <div style={{
      position: "absolute", left: "67%", top: 400,
      fontFamily: "var(--vg-display)", fontSize: 26, fontWeight: 700,
      color: "var(--vg-blood-glow)", letterSpacing: "0.06em",
      textShadow: "0 0 8px rgba(184,30,30,0.6), 0 1px 0 #000",
      transform: "rotate(2deg)", opacity: 0.85,
    }}>1&nbsp;104</div>
    <div style={{
      position: "absolute", left: "70%", top: 470,
      fontFamily: "var(--vg-serif)", fontStyle: "italic", fontSize: 16,
      color: "var(--vg-aspect-bright)", letterSpacing: "0.1em",
      textShadow: "0 0 6px rgba(0,0,0,0.85)",
    }}>· entzündet ·</div>
  </>
);

// -------------------------------------------------------------------------
// BOTTOM CHROME — the diegetic occult tome
// -------------------------------------------------------------------------

const BottomChrome = ({ life, mana, spirit, lifePct, manaPct, spiritPct, xpPct, skills, aspect }) => {
  const A = ASPECT_GLYPHS[aspect] || ASPECT_GLYPHS.valsa;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 264, pointerEvents: "none" }}>
      {/* parchment slab background */}
      <svg viewBox="0 0 1920 264" width="1920" height="264" preserveAspectRatio="none" style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="slab" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#0a0604" stopOpacity="0"/>
            <stop offset="20%" stopColor="#1a0e08" stopOpacity="0.9"/>
            <stop offset="100%" stopColor="#050200" stopOpacity="1"/>
          </linearGradient>
          <linearGradient id="bronze" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#9a7642"/>
            <stop offset="50%" stopColor="#5a3f24"/>
            <stop offset="100%" stopColor="#3b2818"/>
          </linearGradient>
        </defs>
        <rect width="1920" height="264" fill="url(#slab)"/>
        {/* top edge — bronze rail with hammered notches */}
        <rect x="0" y="44" width="1920" height="3" fill="url(#bronze)" opacity="0.9"/>
        <rect x="0" y="49" width="1920" height="1" fill="#000" opacity="0.6"/>
        {/* notches */}
        {Array.from({ length: 64 }).map((_, i) => (
          <rect key={i} x={i*30 + 6} y="44" width="2" height="6" fill="#000" opacity="0.5"/>
        ))}
      </svg>

      {/* center — skill bar + spirit rail + xp rail */}
      <div style={{
        position: "absolute", left: "50%", bottom: 32, transform: "translateX(-50%)",
        display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
        pointerEvents: "auto",
      }}>
        {/* SPIRIT rail (gold) */}
        <div style={{ width: 720, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.35em", color: "var(--vg-gold)", width: 72, textAlign: "right" }}>
            GEIST
          </div>
          <div className="vg-bar" style={{ flex: 1, height: 14 }}>
            <div className="vg-bar__fill vg-bar__fill--spirit" style={{ width: `${spiritPct*100}%` }}/>
            <div className="vg-bar__sheen"/>
            <div className="vg-bar__notches"/>
            {/* reservation marker */}
            <div style={{ position: "absolute", left: "68.75%", top: -2, bottom: -2, width: 1, background: "#000" }}/>
            <div style={{ position: "absolute", left: "68.75%", top: -2, bottom: -2, right: 0, background: "repeating-linear-gradient(45deg, rgba(0,0,0,0.55) 0 4px, transparent 4px 8px)" }}/>
          </div>
          <div style={{ fontFamily: "var(--vg-mono)", fontSize: 11, color: "var(--vg-gold-bright)", width: 80, textShadow: "0 0 6px rgba(0,0,0,0.85)" }}>
            {spirit.cur}/{spirit.max}
          </div>
        </div>

        {/* SKILL BAR */}
        <div style={{
          position: "relative", padding: "14px 18px 16px",
          background: "linear-gradient(180deg, rgba(28,18,10,0.95), rgba(8,5,3,0.95))",
          border: "1px solid var(--vg-bronze)",
          boxShadow: "inset 0 0 30px rgba(0,0,0,0.75), 0 0 0 1px #000, 0 0 30px rgba(0,0,0,0.6)",
        }}>
          {/* corners */}
          <div style={{ position:"absolute", top:-3, left:-3 }}><OrnamentCorner size={22} rotate={0} stroke="var(--vg-aspect)"/></div>
          <div style={{ position:"absolute", top:-3, right:-3 }}><OrnamentCorner size={22} rotate={90} stroke="var(--vg-aspect)"/></div>
          <div style={{ position:"absolute", bottom:-3, right:-3 }}><OrnamentCorner size={22} rotate={180} stroke="var(--vg-aspect)"/></div>
          <div style={{ position:"absolute", bottom:-3, left:-3 }}><OrnamentCorner size={22} rotate={270} stroke="var(--vg-aspect)"/></div>

          <div style={{ display: "flex", gap: 10 }}>
            {skills.map(s => <SkillSlot key={s.id} {...s}/>)}
            {/* divider */}
            <div style={{ width: 1, background: "var(--vg-bronze-deep)", marginInline: 4 }}/>
            {/* flasks */}
            <FlaskSlot kind="life" pct={0.72} keyHint="A" label="Lebenstrank" />
            <FlaskSlot kind="mana" pct={0.55} keyHint="S" label="Geistestrank" />
          </div>
        </div>

        {/* XP rail */}
        <div style={{ width: 720, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.35em", color: "var(--vg-bronze-warm)", width: 72, textAlign: "right" }}>
            STUFE
          </div>
          <div style={{
            flex: 1, height: 3, background: "#060300", border: "1px solid var(--vg-bronze-deep)",
            position: "relative",
          }}>
            <div style={{
              width: `${xpPct*100}%`, height: "100%",
              background: "linear-gradient(90deg, var(--vg-gold-deep), var(--vg-gold-leaf))",
              boxShadow: "0 0 4px var(--vg-gold-bright)",
            }}/>
          </div>
          <div style={{ fontFamily: "var(--vg-mono)", fontSize: 10, color: "var(--vg-bronze-light)", width: 80 }}>
            XLVII · 62%
          </div>
        </div>
      </div>

      {/* LIFE ORB — left */}
      <ResourceOrb
        kind="life" pct={lifePct} value={`${life.cur}`} max={`${life.max}`} label="LEBEN"
        cssVar="var(--vg-blood)" cssVarBright="var(--vg-blood-glow)"
        side="left"
      />

      {/* MANA ORB — right */}
      <ResourceOrb
        kind="mana" pct={manaPct} value={`${mana.cur}`} max={`${mana.max}`} label="GEIST"
        cssVar="var(--vg-ghost)" cssVarBright="var(--vg-ghost-bright)"
        side="right"
      />
    </div>
  );
};

const SkillSlot = ({ hot, name, cost, kind, gem, ready, cd, icon: Icon, reserved }) => {
  const accent = {
    fire:      "var(--vg-blood-glow)",
    cold:      "var(--vg-ghost-bright)",
    lightning: "var(--vg-aspect-bright)",
    spirit:    "var(--vg-gold-bright)",
  }[kind] || "var(--vg-aspect-bright)";
  return (
    <div style={{
      position: "relative", width: 76, height: 88,
      background: "linear-gradient(160deg, #1a1108 0%, #0a0604 60%, #050200 100%)",
      border: `1px solid ${ready ? accent : "var(--vg-bronze-deep)"}`,
      boxShadow: `inset 0 0 14px rgba(0,0,0,0.85), 0 0 ${ready ? '10px' : '0'} ${accent}40`,
      color: accent,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      cursor: "pointer",
      opacity: ready ? 1 : 0.85,
    }}>
      {/* studs */}
      <span style={{ position:"absolute", top:-2, left:-2, width:5, height:5, background:accent }}/>
      <span style={{ position:"absolute", top:-2, right:-2, width:5, height:5, background:accent }}/>
      <span style={{ position:"absolute", bottom:-2, left:-2, width:5, height:5, background:accent }}/>
      <span style={{ position:"absolute", bottom:-2, right:-2, width:5, height:5, background:accent }}/>

      <div style={{ width: 50, height: 50, display: "grid", placeItems: "center" }}>
        <Icon size={44}/>
      </div>
      {/* cooldown sweep */}
      {!ready && cd > 0 && (
        <div style={{ position: "absolute", inset: 4, pointerEvents: "none" }}>
          <div style={{
            position: "absolute", inset: 0,
            background: `conic-gradient(rgba(0,0,0,0.7) ${(1-cd)*360}deg, transparent 0)`,
          }}/>
          <div style={{
            position: "absolute", inset: 0, display: "grid", placeItems: "center",
            fontFamily: "var(--vg-mono)", fontSize: 18, fontWeight: 700,
            color: "var(--vg-vellum-pale)", textShadow: "0 0 4px #000",
          }}>{(cd*4.2).toFixed(1)}</div>
        </div>
      )}
      {/* hotkey */}
      <div style={{
        position: "absolute", top: 4, left: 4,
        width: 16, height: 16, display: "grid", placeItems: "center",
        background: "rgba(0,0,0,0.7)", border: `1px solid ${accent}88`,
        fontFamily: "var(--vg-display)", fontSize: 10, fontWeight: 700, color: "var(--vg-vellum-pale)",
      }}>{hot}</div>
      {/* cost */}
      <div style={{
        position: "absolute", bottom: 3, right: 4,
        fontFamily: "var(--vg-mono)", fontSize: 9, color: kind === "spirit" ? "var(--vg-gold-bright)" : "var(--vg-ghost-bright)",
        textShadow: "0 0 4px #000",
      }}>{reserved ? `−${reserved}` : cost}</div>
      {/* gem label */}
      <div style={{
        position: "absolute", bottom: -16, left: 0, right: 0, textAlign: "center",
        fontFamily: "var(--vg-display)", fontSize: 8, letterSpacing: "0.18em",
        color: "var(--vg-bronze-warm)", textTransform: "uppercase",
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
      }}>{name}</div>
    </div>
  );
};

const FlaskSlot = ({ kind, pct, keyHint, label }) => {
  const accent = kind === "life" ? "var(--vg-blood-glow)" : "var(--vg-ghost-bright)";
  const fill = kind === "life"
    ? "linear-gradient(180deg, #b81e1e 0%, #560c0c 100%)"
    : "linear-gradient(180deg, #7fd0dc 0%, #1a5e6c 100%)";
  return (
    <div style={{ position: "relative", width: 56, height: 88, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end" }}>
      {/* flask glass */}
      <svg viewBox="0 0 56 88" width="56" height="88">
        <defs>
          <clipPath id={`flask-${kind}`}>
            <path d="M22 12 L34 12 L34 24 L38 30 L38 80 L18 80 L18 30 L22 24 Z"/>
          </clipPath>
        </defs>
        {/* fill */}
        <foreignObject x="18" y={80 - 50*pct} width="20" height={50*pct} clipPath={`url(#flask-${kind})`}>
          <div style={{ width: "100%", height: "100%", background: fill, boxShadow: `inset 0 0 8px ${accent}` }}/>
        </foreignObject>
        {/* glass body */}
        <path d="M22 12 L34 12 L34 24 L38 30 L38 80 L18 80 L18 30 L22 24 Z" fill="none" stroke="var(--vg-bronze)" strokeWidth="1.2"/>
        <path d="M22 12 L34 12" stroke="var(--vg-bronze-warm)" strokeWidth="2"/>
        {/* sigil */}
        <text x="28" y="62" textAnchor="middle" fontFamily="var(--vg-display)" fontWeight="700" fontSize="14" fill="var(--vg-vellum-pale)" opacity="0.65">
          {kind === "life" ? "✚" : "❉"}
        </text>
      </svg>
      <div style={{
        position: "absolute", top: 4, right: 0,
        width: 16, height: 16, display: "grid", placeItems: "center",
        background: "rgba(0,0,0,0.7)", border: `1px solid ${accent}88`,
        fontFamily: "var(--vg-display)", fontSize: 10, color: "var(--vg-vellum-pale)",
      }}>{keyHint}</div>
      <div style={{
        position: "absolute", bottom: -16, left: 0, right: 0, textAlign: "center",
        fontFamily: "var(--vg-display)", fontSize: 8, letterSpacing: "0.16em",
        color: "var(--vg-bronze-warm)", textTransform: "uppercase",
      }}>{kind === "life" ? "Trank" : "Geist"}</div>
    </div>
  );
};

const ResourceOrb = ({ kind, pct, value, max, label, cssVar, cssVarBright, side }) => {
  // huge gilded orb in lower corner
  const size = 220;
  const pos = side === "left"
    ? { left: 24, bottom: 24 }
    : { right: 24, bottom: 24 };
  return (
    <div style={{ position: "absolute", ...pos, width: size, height: size, pointerEvents: "auto" }}>
      {/* outer bronze frame */}
      <svg viewBox="0 0 220 220" width={size} height={size} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <radialGradient id={`g-${kind}`} cx="50%" cy="38%" r="60%">
            <stop offset="0%" stopColor={cssVarBright}/>
            <stop offset="60%" stopColor={cssVar}/>
            <stop offset="100%" stopColor="#0a0604"/>
          </radialGradient>
          <clipPath id={`clip-${kind}`}>
            <circle cx="110" cy="110" r="86"/>
          </clipPath>
        </defs>
        {/* bronze outer ring */}
        <circle cx="110" cy="110" r="104" fill="none" stroke="#3b2818" strokeWidth="6"/>
        <circle cx="110" cy="110" r="100" fill="none" stroke="var(--vg-bronze)" strokeWidth="2"/>
        <circle cx="110" cy="110" r="96"  fill="none" stroke="var(--vg-bronze-warm)" strokeWidth="1"/>
        <circle cx="110" cy="110" r="88"  fill="#050302"/>
        {/* fill */}
        <g clipPath={`url(#clip-${kind})`}>
          <rect x="24" y={24 + 172*(1-pct)} width="172" height={172*pct} fill={`url(#g-${kind})`}/>
          {/* surface wobble */}
          <path d={`M 24 ${24 + 172*(1-pct)} Q 67 ${24 + 172*(1-pct) - 5} 110 ${24 + 172*(1-pct)} T 196 ${24 + 172*(1-pct)}`} stroke={cssVarBright} strokeWidth="1.5" fill="none" opacity="0.8"/>
          {/* inner glow */}
          <circle cx="110" cy="110" r="86" fill={`radial-gradient(circle, ${cssVarBright} 0%, transparent 60%)`} opacity="0.5"/>
        </g>
        {/* ticks around */}
        {Array.from({ length: 48 }).map((_, i) => {
          const a = (i * Math.PI * 2) / 48;
          const r1 = 92, r2 = i % 4 === 0 ? 100 : 96;
          return <line key={i}
            x1={110 + Math.cos(a)*r1} y1={110 + Math.sin(a)*r1}
            x2={110 + Math.cos(a)*r2} y2={110 + Math.sin(a)*r2}
            stroke="var(--vg-bronze-warm)" strokeWidth={i%4===0 ? 1.4 : 0.6} opacity={i%4===0 ? 0.9 : 0.5}
          />;
        })}
        {/* studs N/E/S/W */}
        {[0, 90, 180, 270].map(a => {
          const rad = a*Math.PI/180;
          const cx = 110 + Math.cos(rad)*104, cy = 110 + Math.sin(rad)*104;
          return <g key={a}>
            <circle cx={cx} cy={cy} r="6" fill="var(--vg-bronze-warm)"/>
            <circle cx={cx} cy={cy} r="3" fill="var(--vg-aspect-bright)"/>
          </g>;
        })}
      </svg>
      {/* value overlay */}
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", pointerEvents: "none",
      }}>
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 9, letterSpacing: "0.3em", color: cssVarBright,
          textShadow: "0 0 8px #000",
        }}>{label}</div>
        <div style={{
          fontFamily: "var(--vg-display)", fontSize: 30, fontWeight: 700, color: "var(--vg-vellum-pale)",
          textShadow: "0 0 10px #000, 0 0 4px " + cssVar,
          letterSpacing: "0.04em",
        }}>{value}</div>
        <div style={{
          fontFamily: "var(--vg-mono)", fontSize: 12, color: cssVarBright,
          textShadow: "0 0 6px #000",
        }}>von {max}</div>
      </div>
    </div>
  );
};

window.HudScreen = HudScreen;
