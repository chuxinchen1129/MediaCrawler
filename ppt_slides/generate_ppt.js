const html2pptx = require('/Users/echo/.claude/plugins/cache/anthropic-agent-skills/example-skills/69c0b1a06741/skills/pptx/scripts/html2pptx.js');

async function generatePresentation() {
    const pptx = new (require('pptxgenjs'))();
    pptx.layout = 'LAYOUT_16x9';

    // Slide 1: Cover
    await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide01-cover.html', pptx);

    // Slide 2: Table of Contents
    await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide02-toc.html', pptx);

    // Slide 3: Data Overview
    await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide03-data-overview.html', pptx);

    // Slide 4: Willingness Analysis with Pie Chart
    const { slide: slide4, placeholders: p4 } = await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide04-willingness.html', pptx);
    slide4.addChart(pptx.ChartType.pie, [
        { name: '愿意尝试', labels: ['愿意尝试'], values: [78.6] },
        { name: '不愿意尝试', labels: ['不愿意尝试'], values: [21.4] }
    ], {
        x: 0.5, y: 1.5, w: 3.5, h: 3.0,
        chartColors: ['5EA8A7', 'FE4447'],
        showLegend: true,
        legendPos: 'r',
        dataLabelFormatCode: '0.0%"'
    });

    // Slide 5: Willing Reasons with Horizontal Bar Chart
    const { slide: slide5, placeholders: p5 } = await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide05-willing-reasons.html', pptx);
    slide5.addChart(pptx.ChartType.bar, [
        { name: '提及率', labels: ['口感好', '社交/聚会', '健身/减肥', '好奇尝鲜', '替代传统啤酒'], values: [50.7, 11.1, 9.0, 8.3, 6.5] }
    ], {
        x: 0.5, y: 1.3, w: 6.2, h: 3.5,
        barDir: 'bar',
        chartColors: ['5EA8A7'],
        showLegend: false,
        dataLabelFormatCode: '0.0%"',
        valAxisHidden: false,
        showValue: true
    });

    // Slide 6: Unwilling Reasons with Horizontal Bar Chart
    const { slide: slide6, placeholders: p6 } = await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide06-unwilling-reasons.html', pptx);
    slide6.addChart(pptx.ChartType.bar, [
        { name: '提及率', labels: ['口感不好', '失望体验', '价格/性价比'], values: [48.3, 32.3, 10.5] }
    ], {
        x: 0.5, y: 1.3, w: 6.2, h: 3.5,
        barDir: 'bar',
        chartColors: ['FE4447'],
        showLegend: false,
        dataLabelFormatCode: '0.0%"',
        valAxisHidden: false,
        showValue: true
    });

    // Slide 7: Scenarios with Column Chart
    const { slide: slide7, placeholders: p7 } = await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide07-scenarios.html', pptx);
    slide7.addChart(pptx.ChartType.bar, [
        { name: '提及次数', labels: ['聚会', '开车', '健身', '夏天', '宵夜', '火锅', '居家', '减肥'], values: [82, 49, 39, 35, 32, 28, 24, 22] }
    ], {
        x: 0.5, y: 1.2, w: 6.2, h: 2.5,
        barDir: 'col',
        chartColors: ['5EA8A7'],
        showLegend: false,
        dataLabelFormatCode: '0',
        valAxisHidden: false,
        showValue: true
    });

    // Slide 8: User Personas
    await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide08-personas.html', pptx);

    // Slide 9: Insights and Recommendations
    await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide09-insights.html', pptx);

    // Slide 10: Closing
    await html2pptx('/Users/echo/MediaCrawler/ppt_slides/slide10-closing.html', pptx);

    // Save presentation
    await pptx.writeFile({ fileName: '/Users/echo/MediaCrawler/无醇啤酒消费者意愿与场景语义分析.pptx' });
    console.log('PPT生成成功！');
}

generatePresentation().catch(console.error);
