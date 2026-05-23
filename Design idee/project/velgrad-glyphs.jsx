/* global React */

// =========================================================================
// VELGRAD — Glyph & ornament library
// Aspect glyphs from lore, plus filigree borders, item icons, hex shapes.
// =========================================================================

// -------------------------------------------------------------------------
// 1. ASPEKT-GLYPHEN (the Seven)
// -------------------------------------------------------------------------

const GlyphKharn = ({ size = 64, stroke = "currentColor", fill = "none" }) => (
  // Open anvil with a tear in its center
  <svg viewBox="0 0 64 64" width={size} height={size} fill={fill} stroke={stroke} strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 38 L18 30 L46 30 L54 38 L48 38 L48 44 L16 44 L16 38 Z" />
    <path d="M22 30 L22 22 L42 22 L42 30" />
    <path d="M26 22 L26 14 M38 22 L38 14" />
    <path d="M22 44 L22 52 L42 52 L42 44" />
    {/* tear */}
    <path d="M32 33 C30 35.5 30 38 32 39.5 C34 38 34 35.5 32 33 Z" fill={stroke} opacity="0.9"/>
    {/* serif arms */}
    <path d="M8 38 L12 38 M52 38 L56 38" />
  </svg>
);

const GlyphNheyra = ({ size = 64, stroke = "currentColor" }) => (
  // Two interlocked circles, one light, one dark — phases of time
  <svg viewBox="0 0 64 64" width={size} height={size} fill="none" stroke={stroke} strokeWidth="1.25">
    <circle cx="25" cy="32" r="14" />
    <circle cx="39" cy="32" r="14" />
    <path d="M25 18 A14 14 0 0 1 25 46 A14 14 0 0 1 25 18 Z" fill={stroke} opacity="0.18"/>
    <path d="M39 18 A14 14 0 0 1 39 46" fill={stroke} opacity="0.35"/>
    {/* hour ticks */}
    {[0,45,90,135,180,225,270,315].map(a => {
      const r1 = 18, r2 = 21;
      const rad = (a * Math.PI) / 180;
      const x1 = 32 + Math.cos(rad) * r1, y1 = 32 + Math.sin(rad) * r1;
      const x2 = 32 + Math.cos(rad) * r2, y2 = 32 + Math.sin(rad) * r2;
      return <line key={a} x1={x1} y1={y1} x2={x2} y2={y2} opacity="0.45"/>;
    })}
  </svg>
);

const GlyphOusen = ({ size = 64, stroke = "currentColor" }) => (
  // Eye with three pupils
  <svg viewBox="0 0 64 64" width={size} height={size} fill="none" stroke={stroke} strokeWidth="1.25" strokeLinecap="round">
    <path d="M6 32 C18 18 46 18 58 32 C46 46 18 46 6 32 Z" />
    <circle cx="32" cy="32" r="11" />
    {/* three pupils in a triangle */}
    <circle cx="32" cy="27" r="2.2" fill={stroke}/>
    <circle cx="28" cy="35" r="2.2" fill={stroke}/>
    <circle cx="36" cy="35" r="2.2" fill={stroke}/>
    {/* lash flecks */}
    <path d="M10 25 L7 22 M32 18 L32 14 M54 25 L57 22 M10 39 L7 42 M54 39 L57 42 M32 46 L32 50" />
  </svg>
);

const GlyphValsa = ({ size = 64, stroke = "currentColor" }) => (
  // Hand grasping a flame, unburned
  <svg viewBox="0 0 64 64" width={size} height={size} fill="none" stroke={stroke} strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
    {/* flame */}
    <path d="M32 8 C28 16 24 20 24 28 C24 34 28 38 32 38 C36 38 40 34 40 28 C40 22 36 18 32 8 Z" fill={stroke} opacity="0.22"/>
    <path d="M32 14 C30 20 28 22 28 27 C28 31 30 33 32 33 C34 33 36 31 36 27 C36 22 34 20 32 14 Z" opacity="0.7"/>
    {/* hand grasping */}
    <path d="M18 36 C18 34 20 32 22 32 L26 32" />
    <path d="M18 40 L26 40" />
    <path d="M20 44 L28 44" />
    <path d="M22 48 L32 48 L42 48" />
    <path d="M46 36 C46 34 44 32 42 32 L38 32" />
    <path d="M46 40 L38 40" />
    <path d="M44 44 L36 44" />
    {/* wrist */}
    <path d="M22 52 L42 52 L40 56 L24 56 Z" opacity="0.6"/>
  </svg>
);

const GlyphImNesh = ({ size = 64, stroke = "currentColor", strike = true }) => (
  // Broken tongue on a book — and a strikethrough (exkommuniziert)
  <svg viewBox="0 0 64 64" width={size} height={size} fill="none" stroke={stroke} strokeWidth="1.25" strokeLinejoin="round">
    {/* book */}
    <path d="M10 22 L32 18 L54 22 L54 50 L32 46 L10 50 Z" />
    <path d="M32 18 L32 46" />
    <path d="M14 26 L28 24 M14 30 L28 28 M14 34 L28 32 M36 24 L50 26 M36 28 L50 30 M36 32 L50 34" opacity="0.45"/>
    {/* broken tongue */}
    <path d="M28 36 L30 42 L34 38 L36 42 L38 36" />
    {strike && <line x1="6" y1="58" x2="58" y2="6" stroke={stroke} strokeWidth="2.5" opacity="0.85"/>}
  </svg>
);

const GlyphShulavh = ({ size = 64, stroke = "currentColor" }) => (
  // Three interwoven threads — red, black, white (we render as stroke + dashes)
  <svg viewBox="0 0 64 64" width={size} height={size} fill="none" strokeWidth="1.6" strokeLinecap="round">
    <path d="M16 16 C24 28 40 28 48 40" stroke={stroke} opacity="0.9"/>
    <path d="M16 32 C24 24 40 40 48 32" stroke={stroke} opacity="0.6" strokeDasharray="2 3"/>
    <path d="M16 48 C24 36 40 36 48 24" stroke={stroke} opacity="0.85" strokeDasharray="1 2"/>
    {/* knot */}
    <circle cx="32" cy="32" r="3" fill={stroke}/>
  </svg>
);

const GlyphHollow = ({ size = 64, stroke = "currentColor" }) => (
  // The void — a frame around nothing
  <svg viewBox="0 0 64 64" width={size} height={size} fill="none" stroke={stroke} strokeWidth="1" strokeDasharray="2 3">
    <rect x="14" y="14" width="36" height="36"/>
    <text x="32" y="36" textAnchor="middle" fontSize="9" fill={stroke} fontFamily="serif" fontStyle="italic" opacity="0.55">— nichil —</text>
  </svg>
);

const ASPECT_GLYPHS = {
  kharn: GlyphKharn, nheyra: GlyphNheyra, ousen: GlyphOusen,
  valsa: GlyphValsa, imnesh: GlyphImNesh, shulavh: GlyphShulavh, hollow: GlyphHollow,
};

const ASPECT_LABEL = {
  kharn: { name: "Kharn", domain: "Form" },
  nheyra: { name: "Nheyra", domain: "Zeit" },
  ousen: { name: "Ousen", domain: "Geist" },
  valsa: { name: "Valsa", domain: "Wille" },
  imnesh: { name: "Im-Nesh", domain: "Sprache" },
  shulavh: { name: "Shulavh", domain: "Bindung" },
  hollow: { name: "???", domain: "Vergessen" },
};

// -------------------------------------------------------------------------
// 2. FILIGRANE ORNAMENT-RAHMEN
// -------------------------------------------------------------------------

// A bronze filigree corner. Place 4× in a frame with rotations.
const OrnamentCorner = ({ size = 56, stroke = "var(--vg-bronze-warm)", rotate = 0 }) => (
  <svg viewBox="0 0 56 56" width={size} height={size} style={{ transform: `rotate(${rotate}deg)` }}
       fill="none" stroke={stroke} strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    {/* outer right-angle */}
    <path d="M2 2 L2 28 M2 2 L28 2" strokeWidth="1.5"/>
    {/* curl inward */}
    <path d="M2 18 C10 18 14 14 14 6"/>
    <path d="M18 2 C18 10 14 14 6 14"/>
    {/* small loops */}
    <circle cx="14" cy="14" r="1.8" fill={stroke} opacity="0.9"/>
    <path d="M14 14 C20 14 24 18 24 24 M14 14 C14 20 18 24 24 24"/>
    {/* flourish trailing */}
    <path d="M2 36 L2 38 M2 42 L2 44 M2 48 L2 50" opacity="0.6"/>
    <path d="M36 2 L38 2 M42 2 L44 2 M48 2 L50 2" opacity="0.6"/>
    <circle cx="2" cy="2" r="2" fill={stroke}/>
  </svg>
);

// Header divider: --— ✦ —--
const OrnamentDivider = ({ width = 240, color = "var(--vg-bronze-warm)" }) => (
  <svg viewBox="0 0 240 14" width={width} height="14" fill="none" stroke={color} strokeWidth="1" strokeLinecap="round">
    <line x1="0" y1="7" x2="92" y2="7" opacity="0.85"/>
    <line x1="148" y1="7" x2="240" y2="7" opacity="0.85"/>
    <line x1="40" y1="3" x2="80" y2="3" opacity="0.4"/>
    <line x1="160" y1="3" x2="200" y2="3" opacity="0.4"/>
    <line x1="40" y1="11" x2="80" y2="11" opacity="0.4"/>
    <line x1="160" y1="11" x2="200" y2="11" opacity="0.4"/>
    {/* center diamond */}
    <path d="M120 1 L126 7 L120 13 L114 7 Z" fill={color} opacity="0.55"/>
    <path d="M120 3.5 L123.5 7 L120 10.5 L116.5 7 Z" fill="var(--vg-vellum)"/>
    {/* flanking dots */}
    <circle cx="100" cy="7" r="1.3" fill={color}/>
    <circle cx="140" cy="7" r="1.3" fill={color}/>
  </svg>
);

// Vertical filigree spine — for between book pages
const OrnamentSpine = ({ height = 600, color = "var(--vg-bronze)" }) => (
  <svg viewBox={`0 0 24 ${height}`} width="24" height={height} fill="none" stroke={color} strokeWidth="1" preserveAspectRatio="none">
    <line x1="12" y1="0" x2="12" y2={height} strokeWidth="1.5"/>
    <line x1="6"  y1="0" x2="6"  y2={height} opacity="0.45"/>
    <line x1="18" y1="0" x2="18" y2={height} opacity="0.45"/>
    {/* repeating knots */}
    {Array.from({ length: Math.floor(height / 80) }).map((_, i) => {
      const y = 40 + i * 80;
      return (
        <g key={i} transform={`translate(12 ${y})`}>
          <circle r="3.5" fill="none" stroke={color}/>
          <circle r="1.2" fill={color}/>
          <path d="M-6 0 L-3.5 0 M3.5 0 L6 0" opacity="0.6"/>
        </g>
      );
    })}
  </svg>
);

// Big illuminated drop-cap — letter with gilded box
const DropCap = ({ letter = "A", size = 96 }) => (
  <div style={{
    width: size, height: size, position: "relative",
    background: "linear-gradient(160deg, #1c1208 0%, #3a2616 60%, #1c1208 100%)",
    border: "1px solid var(--vg-bronze)",
    boxShadow: "inset 0 0 24px rgba(0,0,0,0.7), 0 0 0 4px rgba(0,0,0,0.45), 0 0 0 5px var(--vg-bronze-deep)",
    display: "grid", placeItems: "center",
    flexShrink: 0,
  }}>
    <div className="vg-gilded" style={{
      fontFamily: "var(--vg-display)", fontWeight: 800,
      fontSize: size * 0.72, lineHeight: 1, letterSpacing: 0,
    }}>{letter}</div>
    {/* corner ornaments */}
    <div style={{ position: "absolute", top: 2, left: 2 }}><OrnamentCorner size={14} rotate={0}/></div>
    <div style={{ position: "absolute", top: 2, right: 2 }}><OrnamentCorner size={14} rotate={90}/></div>
    <div style={{ position: "absolute", bottom: 2, right: 2 }}><OrnamentCorner size={14} rotate={180}/></div>
    <div style={{ position: "absolute", bottom: 2, left: 2 }}><OrnamentCorner size={14} rotate={270}/></div>
  </div>
);

// Reusable filigree frame — wraps children, paints 4 corners + border
const FiligreeFrame = ({ children, padding = 24, corner = 36, style = {}, accent }) => {
  const stroke = accent || "var(--vg-bronze-warm)";
  return (
    <div style={{
      position: "relative",
      padding,
      border: "1px solid var(--vg-bronze-deep)",
      boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.55), inset 0 0 60px rgba(10,7,3,0.55)",
      ...style,
    }}>
      <div style={{ position: "absolute", top: -2, left: -2 }}><OrnamentCorner size={corner} rotate={0} stroke={stroke}/></div>
      <div style={{ position: "absolute", top: -2, right: -2 }}><OrnamentCorner size={corner} rotate={90} stroke={stroke}/></div>
      <div style={{ position: "absolute", bottom: -2, right: -2 }}><OrnamentCorner size={corner} rotate={180} stroke={stroke}/></div>
      <div style={{ position: "absolute", bottom: -2, left: -2 }}><OrnamentCorner size={corner} rotate={270} stroke={stroke}/></div>
      {children}
    </div>
  );
};

// -------------------------------------------------------------------------
// 3. SKILL / ITEM ICONS (small inline SVG, 64×64)
// -------------------------------------------------------------------------

const IconFireball = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||44} height={p.size||44} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
    <path d="M32 6 C26 16 18 22 18 34 C18 44 24 52 32 52 C40 52 46 44 46 34 C46 24 38 16 32 6 Z" fill="currentColor" opacity="0.2"/>
    <path d="M32 14 C28 22 24 26 24 33 C24 39 28 44 32 44 C36 44 40 39 40 33 C40 26 36 22 32 14 Z" opacity="0.85"/>
    <path d="M32 22 C30 26 29 28 29 32 C29 36 30 38 32 38 C34 38 35 36 35 32 C35 28 34 26 32 22 Z" fill="currentColor"/>
  </svg>
);

const IconFrostbolt = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||44} height={p.size||44} fill="none" stroke="currentColor" strokeWidth="1.4">
    <line x1="32" y1="6" x2="32" y2="58"/>
    <line x1="10" y1="32" x2="54" y2="32"/>
    <line x1="14" y1="14" x2="50" y2="50"/>
    <line x1="50" y1="14" x2="14" y2="50"/>
    <path d="M28 10 L32 14 L36 10 M28 54 L32 50 L36 54" />
    <path d="M14 28 L10 32 L14 36 M50 28 L54 32 L50 36" />
    <circle cx="32" cy="32" r="3" fill="currentColor"/>
  </svg>
);

const IconArc = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||44} height={p.size||44} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round">
    <path d="M14 10 L22 22 L16 26 L26 36 L20 42 L34 54"/>
    <path d="M30 26 L38 18 L34 16 L44 8" opacity="0.65"/>
    <circle cx="14" cy="10" r="2" fill="currentColor"/>
    <circle cx="34" cy="54" r="2" fill="currentColor"/>
  </svg>
);

const IconFlameWall = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||44} height={p.size||44} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
    <path d="M8 50 L8 36 C10 38 12 36 14 32 C16 36 18 38 20 34 C22 38 24 36 26 30 C28 36 30 38 32 32 C34 38 36 36 38 30 C40 36 42 38 44 32 C46 38 48 36 50 34 C52 38 54 36 56 32 L56 50 Z" fill="currentColor" opacity="0.22"/>
    <path d="M8 50 L56 50" />
    <path d="M14 50 L14 44 M22 50 L22 42 M30 50 L30 40 M38 50 L38 42 M46 50 L46 44 M54 50 L54 46" opacity="0.5"/>
  </svg>
);

const IconComet = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||44} height={p.size||44} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
    <circle cx="40" cy="22" r="10" fill="currentColor" opacity="0.25"/>
    <circle cx="40" cy="22" r="6" />
    <path d="M34 28 L10 52 M30 22 L8 44 M38 32 L16 54" />
    <path d="M40 14 L40 8 M48 22 L54 22 M46 16 L51 11" opacity="0.6"/>
  </svg>
);

const IconHeraldAsh = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||44} height={p.size||44} fill="none" stroke="currentColor" strokeWidth="1.4">
    <circle cx="32" cy="32" r="12"/>
    <circle cx="32" cy="32" r="20" strokeDasharray="2 4" opacity="0.55"/>
    <circle cx="32" cy="32" r="26" strokeDasharray="1 5" opacity="0.35"/>
    <path d="M32 24 C30 28 28 30 28 33 C28 36 30 38 32 38 C34 38 36 36 36 33 C36 30 34 28 32 24 Z" fill="currentColor" opacity="0.8"/>
  </svg>
);

const IconPotion = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||32} height={p.size||32} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
    <path d="M24 8 L40 8 L40 14 L36 18 L36 24 C44 28 48 38 44 48 C40 56 24 56 20 48 C16 38 20 28 28 24 L28 18 L24 14 Z" />
    <path d="M22 14 L42 14" />
    <path d="M24 44 C30 42 34 42 40 44" fill="currentColor" opacity="0.45"/>
  </svg>
);

const IconScroll = (p) => (
  <svg viewBox="0 0 64 64" width={p.size||32} height={p.size||32} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
    <path d="M14 16 C14 12 18 10 22 10 L46 10 C50 10 52 14 52 16 L52 50 C52 54 48 56 44 56 L18 56 C16 56 14 54 14 52 Z"/>
    <path d="M52 16 L46 16 L46 10" opacity="0.7"/>
    <line x1="22" y1="22" x2="46" y2="22"/>
    <line x1="22" y1="28" x2="42" y2="28"/>
    <line x1="22" y1="34" x2="46" y2="34"/>
    <line x1="22" y1="40" x2="40" y2="40"/>
  </svg>
);

// Generic placeholder item icon (gilded rectangle with center symbol)
const ItemIcon = ({ kind = "tome", size = 56, color }) => {
  const c = color || "var(--vg-aspect-bright)";
  const sym = {
    tome:     <path d="M16 14 L48 14 L48 50 L16 50 Z M22 14 L22 50 M16 22 L22 22 M30 22 L42 22 M30 30 L42 30 M30 38 L42 38" stroke={c} strokeWidth="1.4" fill="none"/>,
    ring:     <g stroke={c} strokeWidth="1.4" fill="none"><circle cx="32" cy="36" r="12"/><path d="M28 24 L24 18 L40 18 L36 24"/></g>,
    amulet:   <g stroke={c} strokeWidth="1.4" fill="none"><path d="M20 14 Q32 24 44 14"/><path d="M32 22 L32 28"/><polygon points="32,28 42,42 32,52 22,42"/></g>,
    staff:    <g stroke={c} strokeWidth="1.4" fill="none" strokeLinecap="round"><line x1="48" y1="10" x2="16" y2="54"/><circle cx="50" cy="11" r="6"/><path d="M48 5 L52 11 L48 17"/></g>,
    robe:     <g stroke={c} strokeWidth="1.4" fill="none"><path d="M22 12 L32 18 L42 12 L48 22 L40 28 L40 52 L24 52 L24 28 L16 22 Z"/><line x1="32" y1="18" x2="32" y2="52"/></g>,
    helm:     <g stroke={c} strokeWidth="1.4" fill="none"><path d="M14 36 C14 20 22 12 32 12 C42 12 50 20 50 36 L50 46 L14 46 Z"/><path d="M32 12 L32 28 M22 26 L26 30 M42 26 L38 30"/></g>,
    gloves:   <g stroke={c} strokeWidth="1.4" fill="none"><path d="M18 16 L18 36 L24 50 L40 50 L46 36 L46 16"/><path d="M22 16 L22 28 M28 14 L28 28 M36 14 L36 28 M42 16 L42 28"/></g>,
    boots:    <g stroke={c} strokeWidth="1.4" fill="none"><path d="M22 10 L30 10 L30 38 L48 38 L48 52 L22 52 Z"/><line x1="22" y1="44" x2="48" y2="44"/></g>,
    belt:     <g stroke={c} strokeWidth="1.4" fill="none"><rect x="10" y="26" width="44" height="12"/><rect x="28" y="22" width="8" height="20"/><line x1="32" y1="26" x2="32" y2="38"/></g>,
    flask:    <g stroke={c} strokeWidth="1.4" fill="none"><path d="M26 10 L38 10 L38 18 L42 24 L42 50 L22 50 L22 24 L26 18 Z"/><path d="M22 36 L42 36" opacity="0.6"/></g>,
    gem:      <g stroke={c} strokeWidth="1.4" fill="none"><polygon points="32,8 50,28 32,56 14,28"/><line x1="14" y1="28" x2="50" y2="28"/><line x1="32" y1="8" x2="32" y2="56" opacity="0.5"/></g>,
    sigil:    <g stroke={c} strokeWidth="1.4" fill="none"><circle cx="32" cy="32" r="20"/><polygon points="32,16 46,40 18,40"/><circle cx="32" cy="34" r="3" fill={c}/></g>,
  }[kind];
  return (
    <svg viewBox="0 0 64 64" width={size} height={size}>
      {sym}
    </svg>
  );
};

// -------------------------------------------------------------------------
// 4. SLOT FRAMES — sockets for equipment/skills/gems
// -------------------------------------------------------------------------

const SocketFrame = ({ children, size = 80, rarity = "common", glyph, onClick, label }) => {
  // rarity color edge
  const rarityColor = {
    common:   "var(--vg-vellum-mid)",
    magic:    "var(--vg-ghost)",
    rare:     "var(--vg-gold-bright)",
    unique:   "#c9742a",
    mythic:   "var(--vg-blood-glow)",
    empty:    "var(--vg-bronze-deep)",
  }[rarity] || "var(--vg-bronze)";

  return (
    <button onClick={onClick} aria-label={label} style={{
      position: "relative",
      width: size, height: size,
      background: "linear-gradient(160deg, #0a0604 0%, #1d1409 50%, #050302 100%)",
      border: `1px solid ${rarityColor}`,
      boxShadow: `inset 0 0 18px rgba(0,0,0,0.85), inset 0 1px 0 rgba(154,118,66,0.18), 0 0 0 1px rgba(0,0,0,0.5)`,
      color: rarityColor,
      cursor: "pointer",
      padding: 0,
    }}>
      {/* mitered corner studs */}
      <span style={{ position:"absolute", top:-2, left:-2, width:6, height:6, background: rarityColor, opacity: 0.9 }}/>
      <span style={{ position:"absolute", top:-2, right:-2, width:6, height:6, background: rarityColor, opacity: 0.9 }}/>
      <span style={{ position:"absolute", bottom:-2, left:-2, width:6, height:6, background: rarityColor, opacity: 0.9 }}/>
      <span style={{ position:"absolute", bottom:-2, right:-2, width:6, height:6, background: rarityColor, opacity: 0.9 }}/>
      <div style={{ width:"100%", height:"100%", display:"grid", placeItems:"center" }}>
        {children}
        {glyph && <div style={{ position:"absolute", bottom:4, right:4, opacity:0.7 }}>{glyph}</div>}
      </div>
    </button>
  );
};

// hex node for skill tree
const HexNode = ({ size = 52, allocated = false, available = false, notable = false, kind, label, onClick }) => {
  const r = size/2;
  const points = [0,1,2,3,4,5].map(i => {
    const a = (Math.PI/3)*i - Math.PI/6;
    return `${r + r*Math.cos(a)},${r + r*Math.sin(a)}`;
  }).join(" ");
  const fillColor = allocated
    ? "var(--vg-aspect)"
    : available ? "rgba(122,90,52,0.45)" : "rgba(20,14,8,0.85)";
  const strokeColor = allocated ? "var(--vg-aspect-bright)" : (notable ? "var(--vg-aspect-deep)" : "var(--vg-bronze-deep)");
  return (
    <button onClick={onClick} aria-label={label} title={label} style={{
      width: size, height: size, padding: 0, border: "none", background: "transparent", cursor: "pointer",
      filter: allocated ? "drop-shadow(0 0 6px var(--vg-aspect-bright))" : "none",
    }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <polygon points={points} fill={fillColor} stroke={strokeColor} strokeWidth={notable ? 2.2 : 1.4}/>
        {notable && <polygon points={points} fill="none" stroke="var(--vg-aspect-bright)" strokeWidth="0.6" transform={`translate(${size*0.13} ${size*0.13}) scale(0.74)`} opacity="0.55"/>}
        {kind && (
          <g transform={`translate(${size/2 - 12} ${size/2 - 12})`}>
            {/* mini symbol per kind */}
            {kind === "fire" && <path d="M12 4 C10 8 8 10 8 14 C8 18 10 20 12 20 C14 20 16 18 16 14 C16 10 14 8 12 4 Z" fill={allocated ? "var(--vg-ink)" : "var(--vg-bronze-warm)"} opacity="0.9"/>}
            {kind === "cold" && <g stroke={allocated ? "var(--vg-ink)" : "var(--vg-ghost)"} strokeWidth="1.2"><line x1="12" y1="3" x2="12" y2="21"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></g>}
            {kind === "lightning" && <path d="M14 4 L8 14 L12 14 L10 20 L16 10 L12 10 Z" fill={allocated ? "var(--vg-ink)" : "var(--vg-aspect-bright)"} stroke="none"/>}
            {kind === "life" && <path d="M12 20 C6 16 4 11 7 7 C9 5 12 6 12 9 C12 6 15 5 17 7 C20 11 18 16 12 20 Z" fill={allocated ? "var(--vg-ink)" : "var(--vg-blood-bright)"} stroke="none"/>}
            {kind === "spirit" && <g><circle cx="12" cy="12" r="5" fill={allocated ? "var(--vg-ink)" : "var(--vg-gold-bright)"}/><circle cx="12" cy="12" r="9" fill="none" stroke={allocated ? "var(--vg-ink)" : "var(--vg-gold)"} strokeWidth="0.7" strokeDasharray="1 2"/></g>}
            {kind === "mana" && <path d="M12 4 C8 10 4 14 6 18 C8 21 16 21 18 18 C20 14 16 10 12 4 Z" fill={allocated ? "var(--vg-ink)" : "var(--vg-ghost-bright)"} stroke="none"/>}
            {kind === "crit" && <path d="M4 12 L20 4 L14 12 L20 20 Z" fill={allocated ? "var(--vg-ink)" : "var(--vg-aspect-bright)"} stroke="none"/>}
          </g>
        )}
      </svg>
    </button>
  );
};

// -------------------------------------------------------------------------
// 5. CONSTELLATION BG — for skill tree + death screen
// -------------------------------------------------------------------------

const ConstellationBackdrop = ({ density = 60, opacity = 0.55, seed = 1 }) => {
  // deterministic pseudo-random
  const rng = (i) => {
    const x = Math.sin(i * 9301 + seed * 49297) * 233280;
    return x - Math.floor(x);
  };
  const stars = Array.from({ length: density }).map((_, i) => ({
    x: rng(i*2)*100,
    y: rng(i*2+1)*100,
    r: 0.4 + rng(i*3)*1.4,
    o: 0.3 + rng(i*5)*0.7,
    delay: rng(i*7) * 4,
  }));
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{
      position:"absolute", inset:0, width:"100%", height:"100%", pointerEvents:"none", opacity,
    }}>
      {stars.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r/10}
          fill="var(--vg-gold-leaf)"
          style={{
            opacity: s.o,
            animation: `vg-ember ${3 + (i%3)}s ease-in-out ${s.delay}s infinite`,
          }}
        />
      ))}
    </svg>
  );
};

// Export everything to window
Object.assign(window, {
  GlyphKharn, GlyphNheyra, GlyphOusen, GlyphValsa, GlyphImNesh, GlyphShulavh, GlyphHollow,
  ASPECT_GLYPHS, ASPECT_LABEL,
  OrnamentCorner, OrnamentDivider, OrnamentSpine, DropCap, FiligreeFrame,
  IconFireball, IconFrostbolt, IconArc, IconFlameWall, IconComet, IconHeraldAsh,
  IconPotion, IconScroll, ItemIcon,
  SocketFrame, HexNode, ConstellationBackdrop,
});
