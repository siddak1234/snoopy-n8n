const { src, dest, series } = require('gulp');
const { exec } = require('child_process');

function runTsc(cb) {
  exec('npx tsc -p tsconfig.json', (error, stdout, stderr) => {
    if (stdout) process.stdout.write(stdout);
    if (stderr) process.stderr.write(stderr);
    cb(error || undefined);
  });
}

function copyAssets() {
  return src(['src/**/*.png', 'src/**/*.svg', 'src/**/*.json'], { allowEmpty: true }).pipe(dest('dist'));
}

exports.build = series(runTsc, copyAssets);
