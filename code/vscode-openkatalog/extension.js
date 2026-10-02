const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

let activeEditor = vscode.window.activeTextEditor;
let decorationTypes = {};
let usageIndex = {};

function activate(context) {
    console.log('=== OPENKATALOG EXTENSION ACTIVATED ===');
    
    decorationTypes.defined = vscode.window.createTextEditorDecorationType({
        color: '#9CDCFE'
    });
    decorationTypes.undefined = vscode.window.createTextEditorDecorationType({
        color: '#4a5568'
    });
    
    const selector = { language: 'openkatalog', scheme: 'file' };
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(selector, { 
            provideHover: function(document, position) {
                console.log('Hover requested at line', position.line, 'col', position.character);
                const result = doProvideHover(document, position);
                console.log('Hover result:', result ? 'found' : 'null');
                return result;
            }
        })
    );
    
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(editor => {
            activeEditor = editor;
            if (editor) updateDecorations();
        })
    );
    
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument(event => {
            if (activeEditor && event.document === activeEditor.document) {
                updateDecorations();
            }
        })
    );
    
    if (activeEditor) updateDecorations();
}

function loadUsageIndex(indexPath) {
    try {
        const content = fs.readFileSync(indexPath, 'utf-8');
        usageIndex = JSON.parse(content);
        console.log('Loaded index:', Object.keys(usageIndex).length, 'vars from', indexPath);
    } catch (e) {
        console.log('Failed to load index:', e.message);
        usageIndex = {};
    }
}

function getIndexFilePath(fileName) {
    let dir = path.dirname(fileName);
    const root = path.parse(dir).root;
    while (dir !== root) {
        if (fs.existsSync(path.join(dir, 'config.cfg'))) {
            return path.join(dir, '.ok', 'usage_index.json');
        }
        dir = path.dirname(dir);
    }
    return null;
}

function updateDecorations() {
    const editor = activeEditor;
    if (!editor) return;
    
    const doc = editor.document;
    if (doc.languageId !== 'openkatalog') {
        console.log('Not openkatalog:', doc.languageId);
        return;
    }
    
    const indexPath = getIndexFilePath(doc.fileName);
    if (indexPath && fs.existsSync(indexPath)) {
        loadUsageIndex(indexPath);
    }
    
    const text = doc.getText();
    const lines = text.split('\n');
    const defined = [];
    const undefined_ranges = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const arrowPos = line.indexOf('->');
        if (arrowPos === -1) continue;
        
        const beforeArrow = line.substring(0, arrowPos);
        const afterArrow = line.substring(arrowPos + 2);
        
        // Case 1: Interpolated string "{var1} {var2}"
        const trimmed = afterArrow.trim();
        if (trimmed.startsWith('"')) {
            const re = /\{([^}]+)\}/g;
            let m;
            while ((m = re.exec(afterArrow)) !== null) {
                const varName = m[1].trim();
                if (!varName) continue;
                const start = arrowPos + 2 + m.index + 1; // skip {
                const len = m[0].length - 2; // exclude { }
                const range = new vscode.Range(i, start, i, start + len);
                const info = usageIndex[varName];
                if (info && info.exists) {
                    defined.push(range);
                } else {
                    undefined_ranges.push(range);
                }
            }
            continue;
        }
        
        // Case 2: Simple variable (possibly with .function())
        const varRe = /([a-zA-Z_]\w*)/g;
        let vm;
        while ((vm = varRe.exec(afterArrow)) !== null) {
            const varName = vm[1];
            if (varName.startsWith('$')) continue;
            
            const startInAfter = vm.index;
            const endInAfter = startInAfter + varName.length;
            
            // Skip if followed by .function()
            const rest = afterArrow.substring(endInAfter).trim();
            if (rest.startsWith('.')) continue;
            
            const start = arrowPos + 2 + startInAfter;
            const range = new vscode.Range(i, start, i, start + varName.length);
            
            const info = usageIndex[varName];
            console.log(`Line ${i}: "${varName}" at col ${start}, exists=${info && info.exists}`);
            
            if (info && info.exists) {
                defined.push(range);
            } else {
                undefined_ranges.push(range);
            }
        }
    }
    
    editor.setDecorations(decorationTypes.defined, defined);
    editor.setDecorations(decorationTypes.undefined, undefined_ranges);
    console.log(`Decorations: ${defined.length} defined, ${undefined_ranges.length} undefined`);
}

function doProvideHover(document, position) {
    // Ensure index is loaded
    if (Object.keys(usageIndex).length === 0) {
        const indexPath = getIndexFilePath(document.fileName);
        if (indexPath && fs.existsSync(indexPath)) {
            loadUsageIndex(indexPath);
        }
    }
    
    const line = document.lineAt(position.line).text;
    const arrowPos = line.indexOf('->');
    if (arrowPos === -1) return null;
    
    const afterArrow = line.substring(arrowPos + 2);
    const cursorPos = position.character - (arrowPos + 2);
    
    if (cursorPos < 0) return null;
    
    // Check interpolated strings
    const trimmed = afterArrow.trim();
    if (trimmed.startsWith('"')) {
        const re = /\{([^}]+)\}/g;
        let m;
        while ((m = re.exec(afterArrow)) !== null) {
            const varName = m[1].trim();
            if (!varName) continue;
            if (!usageIndex.hasOwnProperty(varName)) continue;
            
            const start = m.index;
            const end = m.index + m[0].length;
            if (cursorPos >= start && cursorPos <= end) {
                return makeHover(varName);
            }
        }
        return null;
    }
    
    // Check simple variable
    const varRe = /([a-zA-Z_]\w*)/g;
    let vm;
    while ((vm = varRe.exec(afterArrow)) !== null) {
        const varName = vm[1];
        if (varName.startsWith('$')) continue;
        if (!usageIndex.hasOwnProperty(varName)) continue;
        
        const start = vm.index;
        const end = start + varName.length;
        
        if (cursorPos >= start && cursorPos <= end) {
            // Skip if it's a function call
            const rest = afterArrow.substring(end).trim();
            if (rest.startsWith('.')) return null;
            return makeHover(varName);
        }
    }
    
    return null;
}

function makeHover(varName) {
    console.log('makeHover called for:', varName, 'index keys:', Object.keys(usageIndex).slice(0, 5));
    const info = usageIndex[varName];
    console.log('info for', varName, ':', info ? `exists=${info.exists}` : 'undefined');
    const md = new vscode.MarkdownString();
    
    if (!info) {
        md.appendCodeblock(`"${varName}" - NOT IN INDEX`, 'openkatalog');
        return new vscode.Hover(md);
    }
    
    if (!info.exists) {
        md.appendMarkdown(`**${varName}** - ⚠️ NOT FOUND IN DATA\n\n`);
        md.isTrusted = true;
        return new vscode.Hover(md);
    }
    
    md.appendMarkdown(`**${varName}** - ✅ EXISTS\n\n`);
    
    const dataLocations = info.data_locations || [];
    md.appendCodeblock(`${dataLocations.length} data location(s)`, 'openkatalog');
    md.appendMarkdown('\n\n');
    dataLocations.slice(0, 20).forEach(r => {
        if (r.type === 'key' && r.value !== undefined) {
            md.appendMarkdown(`- \`${r.file}\`: **"${r.value}"**\n`);
        } else if (r.type === 'file') {
            md.appendMarkdown(`- \`${r.file}\`\n`);
        } else if (r.type === 'global') {
            md.appendMarkdown(`- \`${r.file}\`: **"${r.value}"**\n`);
        } else {
            md.appendMarkdown(`- \`${r.file}\`\n`);
        }
    });
    md.isTrusted = true;
    return new vscode.Hover(md);
}

function deactivate() {}

module.exports = { activate, deactivate };
