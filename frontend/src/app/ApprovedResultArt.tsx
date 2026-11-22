/** Decorative anonymous profiles: the same three-to-one idea as the approved reference.
 * No founder data is drawn here, and this image never receives salary inputs.
 */
export default function ApprovedResultArt() {
  return (
    <svg className="vb-ref-result-art-svg" viewBox="0 0 570 520" role="img" aria-label="Three anonymous founder silhouettes converge into one aggregate arrow">
      <defs>
        <pattern id="vb-result-dots" width="16" height="16" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r=".9" fill="#171212" opacity=".15" />
        </pattern>
      </defs>
      <path d="M0 0 395 0 475 117 570 140 570 310 368 416 0 520Z" fill="#e40e24"/>
      <path d="M0 56 276 6 470 163 0 204Z" fill="#fff7eb"/>
      <path d="M0 209 326 145 493 242 0 358Z" fill="#fff7eb"/>
      <path d="M0 362 342 298 481 354 0 517Z" fill="#fff7eb"/>
      {[0,1,2].map((i)=>(
        <g key={i} transform={`translate(0 ${i*156})`}>
          <path d="M-25 49 70 8 177 20 309 99 438 120 500 141 462 161 288 124 124 145 0 139Z" fill="#111"/>
          {/* Anonymous silhouette: jagged hair, face profile, jacket. */}
          <path d="M29 98 31 76 24 57 40 40 29 26 52 31 56 17 72 25 87 10 97 27 117 20 117 41 143 43 130 58 153 73 137 80 140 105 126 114 111 112 105 127 116 138 99 143 89 128 70 127 58 142 16 144 12 120Z" fill="#161313"/>
          <path d="M119 66 138 75 153 80 146 88 131 90 133 99 124 112 108 108 97 120 93 143 66 143 75 106 63 84 85 62Z" fill="#161313"/>
          <path d="M135 91 128 94" fill="none" stroke="#fff4e4" strokeWidth="3" opacity=".6"/>
        </g>
      ))}
      <path d="M0 170Q270 152 523 259" fill="none" stroke="#f5ede1" strokeWidth="20"/>
      <path d="M0 335Q263 329 523 259" fill="none" stroke="#fff7ed" strokeWidth="18"/>
      <path d="M0 494Q263 470 523 259" fill="none" stroke="#fff7ed" strokeWidth="18"/>
      <path d="M376 254 526 255 507 236 567 258 505 284 523 265 378 266Z" fill="#111"/>
      <path d="M0 25h118M18 485h110" stroke="#121010" strokeWidth="3" opacity=".25"/>
      <rect width="570" height="520" fill="url(#vb-result-dots)" pointerEvents="none"/>
    </svg>
  );
}
