import { cpSync, copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const vendorFiles = [
    {
        packageName: "alpinejs",
        source: "node_modules/alpinejs/dist/cdn.min.js",
        target: "frontend/static/vendor/alpinejs/alpine.min.js",
    },
    {
        packageName: "chart.js",
        source: "node_modules/chart.js/dist/chart.umd.min.js",
        target: "frontend/static/vendor/chartjs/chart.umd.min.js",
    },
    {
        packageName: "pdfjs-dist",
        source: "node_modules/pdfjs-dist/build/pdf.min.mjs",
        target: "frontend/static/vendor/pdfjs/pdf.min.mjs",
    },
    {
        packageName: "pdfjs-dist",
        source: "node_modules/pdfjs-dist/build/pdf.worker.min.mjs",
        target: "frontend/static/vendor/pdfjs/pdf.worker.min.mjs",
    },
    {
        packageName: "pdfjs-dist",
        source: "node_modules/pdfjs-dist/build/pdf.sandbox.min.mjs",
        target: "frontend/static/vendor/pdfjs/pdf.sandbox.min.mjs",
    },
];

const vendorDirectories = [
    {
        packageName: "pdfjs-dist",
        source: "node_modules/pdfjs-dist/cmaps",
        target: "frontend/static/vendor/pdfjs/cmaps",
    },
    {
        packageName: "pdfjs-dist",
        source: "node_modules/pdfjs-dist/standard_fonts",
        target: "frontend/static/vendor/pdfjs/standard_fonts",
    },
];

const lockfile = JSON.parse(readFileSync("package-lock.json", "utf8"));
const versions = [];

function addPackageVersion(packageName) {
    const packageInfo = lockfile.packages[`node_modules/${packageName}`];
    const versionLine = `${packageName}: ${packageInfo?.version ?? "unknown"}`;
    if (!versions.includes(versionLine)) {
        versions.push(versionLine);
    }
}

for (const file of vendorFiles) {
    mkdirSync(dirname(file.target), { recursive: true });
    copyFileSync(file.source, file.target);

    addPackageVersion(file.packageName);
}

for (const directory of vendorDirectories) {
    mkdirSync(dirname(directory.target), { recursive: true });
    cpSync(directory.source, directory.target, { recursive: true });

    addPackageVersion(directory.packageName);
}

writeFileSync("frontend/static/vendor/VERSIONS.txt", `${versions.join("\n")}\n`, "utf8");
