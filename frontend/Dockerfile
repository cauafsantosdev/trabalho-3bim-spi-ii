FROM node:26.8-alpine

WORKDIR /app

COPY . .

EXPOSE 3000

# SCRUM-19 substituirá este comando pela aplicação Next.js.
CMD ["node", "-e", "require('http').createServer((req,res)=>{res.writeHead(200,{'Content-Type':'text/plain'});res.end('Frontend container OK\\n')}).listen(3000,'0.0.0.0')"]