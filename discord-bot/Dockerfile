# Sử dụng Node.js 20 Alpine siêu nhẹ
FROM node:20-alpine

WORKDIR /app

# Copy package files và cài đặt dependencies trước
COPY package*.json ./
RUN npm install

# Copy toàn bộ mã nguồn bot vào container
COPY . .

# Chạy ở chế độ dev với tsx watch (hoặc npm start sau khi build)
CMD ["npm", "run", "dev"]
