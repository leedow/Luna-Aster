(() => {
  const content = document.getElementById('content');
  const typeSel = document.getElementById('type');
  const urlInput = document.getElementById('url');
  const applyBtn = document.getElementById('apply');
  const resizer = document.getElementById('resizer');
  const toggleTopBtn = document.getElementById('toggleAlwaysOnTop');
  const closeBtn = document.getElementById('close');

  // 默认示例资源
  const defaults = {
    png: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsSAAALEgHS3X78AAABcUlEQVR4nO2aMW7CQBBF3x2U4H1YgS8wQ1EwzN8mWbAopB6mI3m1VJmCkA1WbQO4KdgkRrGf6lFfC2rHkVv8C6mWkH3Kf4KZQb1NfLwYdY0z3ZrZyZtKpC0I6Qm3zCWF1cR9QxK8bA7WqfH3r9v3u+H8S1xkHcXlBpiwW2wV5n8YH2lHcYzU1h8GmX4H6x2Cv2v4a0b6bKXfQb9b0V6z4fB4bBzX0I2zcYUnwJKgEuoS3QO0A6Qb2YFjWJwGkYzKk3rV4gxyyZV8gC4Gv8B5NwGgGq3cZkZ0EoKcH5Kk9QnqOe6UePjKpO9pYwC9Ww4GZzKpS2YFzQk/9A0DkGgtiwvqqvH9AgVgA6oGQwYJ3kK5k+e3jCw3UofWfzQjXbZwKxYyip3JYH2ZQw5FZ1oGf7mJ9D7a6bQkqQkV7iUQf6B7l3h5JxW6u8u/8cK0mBgxZ1cWwVb9iH9m2mJmYv8pQw0CwVgYkY0iU9eL9cW8vY2hQbZ3jQK1b3ySGA3qvAQyOeC7m9+5s0M4o8QO3GqfCjvD5z2p0AAAAAElFTkSuQmCC',
    gif: 'https://media.tenor.com/9GQF6zaPFRIAAAAi/cat-cute.gif'
  };

  let currentType = 'png';

  function clearContent() {
    while (content.firstChild) content.removeChild(content.firstChild);
  }

  function renderPNG(src) {
    clearContent();
    const img = document.createElement('img');
    img.id = 'img';
    img.src = src || defaults.png;
    content.appendChild(img);
  }

  function renderGIF(src) {
    clearContent();
    const img = document.createElement('img');
    img.id = 'img';
    img.src = src || defaults.gif;
    content.appendChild(img);
  }

  function renderWebGL() {
    clearContent();
    const canvas = document.createElement('canvas');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    content.appendChild(canvas);

    const gl = canvas.getContext('webgl', { alpha: true, antialias: true });
    if (!gl) {
      const fallback = document.createElement('div');
      fallback.textContent = 'WebGL 不可用';
      content.appendChild(fallback);
      return;
    }

    const vertSrc = `
      attribute vec2 aPos;
      uniform float uAngle;
      void main(){
        float c = cos(uAngle), s = sin(uAngle);
        mat2 r = mat2(c,-s,s,c);
        gl_Position = vec4(r * aPos, 0.0, 1.0);
      }
    `;
    const fragSrc = `
      precision mediump float;
      void main(){
        gl_FragColor = vec4(1.0, 0.7, 0.2, 0.8);
      }
    `;

    function compile(type, src) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, src);
      gl.compileShader(shader);
      return shader;
    }

    const prog = gl.createProgram();
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, vertSrc));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fragSrc));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    const verts = new Float32Array([
      0, 0.8,
      -0.8, -0.8,
      0.8, -0.8
    ]);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(prog, 'aPos');
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(aPos);
    const uAngle = gl.getUniformLocation(prog, 'uAngle');

    function draw(t){
      const angle = (t * 0.001) % (Math.PI * 2);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0,0,0,0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(uAngle, angle);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);

    window.addEventListener('resize', () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    });
  }

  function renderLive2D(modelUrl) {
    clearContent();
    const info = document.createElement('div');
    info.style.pointerEvents = 'auto';
    info.style.background = 'rgba(0,0,0,0.35)';
    info.style.color = '#fff';
    info.style.padding = '6px 8px';
    info.style.borderRadius = '6px';
    info.textContent = 'Live2D 需要加载第三方库，稍后提供集成示例。';
    content.appendChild(info);
    // 可扩展：动态加载 pixi.js 与 pixi-live2d-display，并渲染 modelUrl
  }

  function apply() {
    const t = typeSel.value;
    const url = urlInput.value.trim();
    currentType = t;
    switch (t) {
      case 'png': return renderPNG(url || defaults.png);
      case 'gif': return renderGIF(url || defaults.gif);
      case 'webgl': return renderWebGL();
      case 'live2d': return renderLive2D(url);
    }
  }

  applyBtn.addEventListener('click', apply);
  typeSel.addEventListener('change', apply);
  window.addEventListener('DOMContentLoaded', apply);

  // 自定义缩放：拖动右下角 resizer
  let resizing = false;
  let startX = 0, startY = 0;
  let startW = 0, startH = 0;
  resizer.addEventListener('mousedown', (e) => {
    resizing = true;
    startX = e.screenX;
    startY = e.screenY;
    startW = window.outerWidth;
    startH = window.outerHeight;
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  function onMove(e){
    if (!resizing) return;
    const dW = e.screenX - startX;
    const dH = e.screenY - startY;
    const newW = Math.max(120, startW + dW);
    const newH = Math.max(120, startH + dH);
    if (window.electronAPI && typeof window.electronAPI.resizeAvatarWindow === 'function') {
      window.electronAPI.resizeAvatarWindow({ width: newW, height: newH });
    }
  }
  function onUp(){
    resizing = false;
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
  }

  toggleTopBtn.addEventListener('click', () => {
    if (window.electronAPI && typeof window.electronAPI.setAvatarAlwaysOnTop === 'function') {
      window.electronAPI.setAvatarAlwaysOnTop(true);
    }
  });
  closeBtn.addEventListener('click', () => {
    if (window.electronAPI && typeof window.electronAPI.closeAvatarWindow === 'function') {
      window.electronAPI.closeAvatarWindow();
    }
  });
})();