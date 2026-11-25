// Render deterministic, 300-dpi PNGs from the persisted SVG figures; no data analysis.
const fs = require('fs');
const path = require('path');
const sharp = require('/Users/alex/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const dir = process.argv[2] || path.join(__dirname, 'figures');
(async()=>{
  for (const name of fs.readdirSync(dir).filter(n=>n.endsWith('.svg')).sort()) {
    const out=path.join(dir,name.replace(/\.svg$/,'.png'));
    if(fs.existsSync(out)) throw new Error('Refusing overwrite');
    await sharp(path.join(dir,name),{density:216}).withMetadata({density:300}).png().toFile(out);
    const meta=await sharp(out).metadata();
    console.log(JSON.stringify({file:path.basename(out),width:meta.width,height:meta.height,dpi:meta.density}));
  }
})().catch(e=>{console.error(e.message);process.exit(1)});
