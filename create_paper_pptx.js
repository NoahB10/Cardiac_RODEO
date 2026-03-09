/**
 * Create Paper Figures PowerPoint
 * Assembles all generated PNG figures into a PowerPoint presentation
 */

const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = __dirname;
const FIGURES_DIR = path.join(PROJECT_ROOT, 'Output', 'PowerPoint_Figures');

// Colors (no # prefix for PptxGenJS)
const COLORS = {
    blue: '6C92ED',
    grey: '888888',
    white: 'FFFFFF',
    black: '000000'
};

async function createPresentation() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.title = 'Cardiac RODEO Paper Figures';
    pptx.author = 'Cardiac RODEO Team';

    // Figure configuration: [figNum, letter, title, notes]
    const figureConfig = [
        ['1', '', 'Figure 1: Pipeline Schematic', 'Placeholder for pipeline schematic'],
        ['2', 'a', 'Figure 2a: SNR Distribution', 'SNR histogram with 0.4 threshold'],
        ['2', 'b', 'Figure 2b: External Images', 'External images placeholder'],
        ['3', 'a', 'Figure 3a: Vandetanib O2 Heatmap', ''],
        ['3', 'b', 'Figure 3b: Vandetanib Contractility Heatmap', ''],
        ['3', 'c', 'Figure 3c: 3D Surface Fit', 'Placeholder for 3D plot'],
        ['3', 'd', 'Figure 3d: R² Equation Comparison', ''],
        ['3', 'e', 'Figure 3e: Random Forest vs Equations', ''],
        ['4', '', 'Figure 4: O2 3D Surface Grid', '5x5 grid of O2 surfaces'],
        ['5', '', 'Figure 5: Contractility 3D Surface Grid', '5x5 grid of Contractility surfaces'],
        ['6', 'a', 'Figure 6a: Arrhythmia ROC Curve', ''],
        ['6', 'b', 'Figure 6b: Arrhythmia Confusion Matrix', ''],
        ['6', 'c', 'Figure 6c: Arrhythmia Metrics', ''],
        ['6', 'd', 'Figure 6d: Arrhythmia Threshold Analysis', ''],
        ['6', 'e', 'Figure 6e: Arrhythmia Cumulative Features', ''],
        ['6', 'f', 'Figure 6f: Arrhythmia SHAP', ''],
        ['6', 'g', 'Figure 6g: MoLFormer ROC Comparison', ''],
        ['6', 'h', 'Figure 6h: MoLFormer Metrics', ''],
        ['7', 'a', 'Figure 7a: Heart Damage ROC Curve', ''],
        ['7', 'b', 'Figure 7b: Heart Damage Confusion Matrix', ''],
        ['7', 'c', 'Figure 7c: Heart Damage Metrics', ''],
        ['7', 'd', 'Figure 7d: Heart Damage Threshold Analysis', ''],
        ['7', 'e', 'Figure 7e: Heart Damage Cumulative Features', ''],
        ['7', 'f', 'Figure 7f: Heart Damage SHAP', ''],
        ['7', 'g', 'Figure 7g: ADMET ROC Comparison', ''],
        ['7', 'h', 'Figure 7h: ADMET Metrics', ''],
        ['8', 'a', 'Figure 8a: Concern ROC Curve', ''],
        ['8', 'b', 'Figure 8b: Concern Confusion Matrix', ''],
        ['8', 'c', 'Figure 8c: Concern Metrics', ''],
        ['8', 'd', 'Figure 8d: Concern Threshold Analysis', ''],
        ['8', 'e', 'Figure 8e: Concern Cumulative Features', ''],
        ['8', 'f', 'Figure 8f: Concern SHAP', ''],
        ['S1', 'a', 'Figure S1a: Vandetanib O2_std', ''],
        ['S1', 'b', 'Figure S1b: Vandetanib O2_dom_freq', ''],
        ['S1', 'c', 'Figure S1c: Vandetanib Amp_dom_freq', ''],
    ];

    for (const [figNum, letter, title, notes] of figureConfig) {
        const figFolder = `Fig_${figNum}`;
        const fileName = letter ? `Fig_${figNum}${letter}.png` : `Fig_${figNum}.png`;
        const imgPath = path.join(FIGURES_DIR, figFolder, fileName);

        const slide = pptx.addSlide();

        // Add title
        slide.addText(title, {
            x: 0.5, y: 0.15, w: 9, h: 0.4,
            fontSize: 18, bold: true, color: COLORS.black, fontFace: 'Arial'
        });

        if (fs.existsSync(imgPath)) {
            // Use fixed layout - center image on slide
            slide.addImage({
                path: imgPath,
                x: 0.5, y: 0.6, w: 9, h: 4.8,
                sizing: { type: 'contain', w: 9, h: 4.8 }
            });
        } else {
            slide.addText('Image not found:\n' + fileName, {
                x: 1, y: 2, w: 8, h: 2,
                fontSize: 14, color: COLORS.grey, align: 'center', valign: 'middle'
            });
        }

        if (notes) slide.addNotes(notes);
    }

    const outputPath = path.join(PROJECT_ROOT, 'Output', 'PowerPoint_Figures', 'Cardiac_RODEO_Paper_Figures.pptx');
    await pptx.writeFile({ fileName: outputPath });
    console.log(`Presentation saved to: ${outputPath}`);
}

createPresentation().catch(console.error);
