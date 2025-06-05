cd `dirname $0`/app/dashboard
export NODE_OPTIONS="--max-old-space-size=4096"
VITE_BASE_API=/api/ npm run build --if-present -- --outDir build --assetsDir statics
cp ./build/index.html ./build/404.html
unset NODE_OPTIONS