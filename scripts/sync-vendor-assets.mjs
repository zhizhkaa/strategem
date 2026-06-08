import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
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
];

const lockfile = JSON.parse(readFileSync("package-lock.json", "utf8"));
const versions = [];

for (const file of vendorFiles) {
    mkdirSync(dirname(file.target), { recursive: true });
    copyFileSync(file.source, file.target);

    const packageInfo = lockfile.packages[`node_modules/${file.packageName}`];
    versions.push(`${file.packageName}: ${packageInfo?.version ?? "unknown"}`);
}

writeFileSync("frontend/static/vendor/VERSIONS.txt", `${versions.join("\n")}\n`, "utf8");
