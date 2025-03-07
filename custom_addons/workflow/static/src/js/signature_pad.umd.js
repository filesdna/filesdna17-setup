/* eslint-disable no-restricted-globals */
/* eslint-disable no-param-reassign */
/* eslint-disable no-undef */
/* eslint-disable no-nested-ternary */
/* eslint-disable no-unused-expressions */
/* eslint-disable func-names */
/*!
 * Signature Pad v3.0.0-beta.4 | https://github.com/szimek/signature_pad
 * (c) 2020 Szymon Nowak | Released under the MIT license
 */
;(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined'
    ? (module.exports = factory())
    : typeof define === 'function' && define.amd
    ? define(factory)
    : ((global =
        typeof globalThis !== 'undefined' ? globalThis : global || self),
      (global.SignaturePad = factory()))
})(this, () => {
  const Point = (function () {
    function Point(x, y, time) {
      this.x = x
      this.y = y
      this.time = time || Date.now()
    }
    Point.prototype.distanceTo = function (start) {
      return Math.sqrt((this.x - start.x) ** 2 + (this.y - start.y) ** 2)
    }
    Point.prototype.equals = function (other) {
      return (
        this.x === other.x && this.y === other.y && this.time === other.time
      )
    }
    Point.prototype.velocityFrom = function (start) {
      return this.time !== start.time
        ? this.distanceTo(start) / (this.time - start.time)
        : 0
    }
    return Point
  })()

  const Bezier = (function () {
    function Bezier(
      startPoint,
      control2,
      control1,
      endPoint,
      startWidth,
      endWidth,
    ) {
      this.startPoint = startPoint
      this.control2 = control2
      this.control1 = control1
      this.endPoint = endPoint
      this.startWidth = startWidth
      this.endWidth = endWidth
    }
    Bezier.fromPoints = function (points, widths) {
      const { c2 } = this.calculateControlPoints(
        points[0],
        points[1],
        points[2],
      )
      const c3 = this.calculateControlPoints(points[1], points[2], points[3]).c1
      return new Bezier(points[1], c2, c3, points[2], widths.start, widths.end)
    }
    Bezier.calculateControlPoints = function (s1, s2, s3) {
      const dx1 = s1.x - s2.x
      const dy1 = s1.y - s2.y
      const dx2 = s2.x - s3.x
      const dy2 = s2.y - s3.y
      const m1 = { x: (s1.x + s2.x) / 2.0, y: (s1.y + s2.y) / 2.0 }
      const m2 = { x: (s2.x + s3.x) / 2.0, y: (s2.y + s3.y) / 2.0 }
      const l1 = Math.sqrt(dx1 * dx1 + dy1 * dy1)
      const l2 = Math.sqrt(dx2 * dx2 + dy2 * dy2)
      const dxm = m1.x - m2.x
      const dym = m1.y - m2.y
      const k = l2 / (l1 + l2)
      const cm = { x: m2.x + dxm * k, y: m2.y + dym * k }
      const tx = s2.x - cm.x
      const ty = s2.y - cm.y
      return {
        c1: new Point(m1.x + tx, m1.y + ty),
        c2: new Point(m2.x + tx, m2.y + ty),
      }
    }
    Bezier.prototype.length = function () {
      const steps = 10
      let length = 0
      let px
      let py
      for (let i = 0; i <= steps; i += 1) {
        const t = i / steps
        const cx = this.point(
          t,
          this.startPoint.x,
          this.control1.x,
          this.control2.x,
          this.endPoint.x,
        )
        const cy = this.point(
          t,
          this.startPoint.y,
          this.control1.y,
          this.control2.y,
          this.endPoint.y,
        )
        if (i > 0) {
          const xdiff = cx - px
          const ydiff = cy - py
          length += Math.sqrt(xdiff * xdiff + ydiff * ydiff)
        }
        px = cx
        py = cy
      }
      return length
    }
    Bezier.prototype.point = function (t, start, c1, c2, end) {
      return (
        start * (1.0 - t) * (1.0 - t) * (1.0 - t) +
        3.0 * c1 * (1.0 - t) * (1.0 - t) * t +
        3.0 * c2 * (1.0 - t) * t * t +
        end * t * t * t
      )
    }
    return Bezier
  })()

  function throttle(fn, wait) {
    if (wait === void 0) {
      wait = 250
    }
    let previous = 0
    let timeout = null
    let result
    let storedContext
    let storedArgs
    const later = function () {
      previous = Date.now()
      timeout = null
      result = fn.apply(storedContext, storedArgs)
      if (!timeout) {
        storedContext = null
        storedArgs = []
      }
    }
    return function wrapper() {
      const args = []
      for (let _i = 0; _i < arguments.length; _i++) {
        args[_i] = arguments[_i]
      }
      const now = Date.now()
      const remaining = wait - (now - previous)
      storedContext = this
      storedArgs = args
      if (remaining <= 0 || remaining > wait) {
        if (timeout) {
          clearTimeout(timeout)
          timeout = null
        }
        previous = now
        result = fn.apply(storedContext, storedArgs)
        if (!timeout) {
          storedContext = null
          storedArgs = []
        }
      } else if (!timeout) {
        timeout = window.setTimeout(later, remaining)
      }
      return result
    }
  }

  const SignaturePad = (function () {
    function SignaturePad(canvas, options) {
      const _this = this
      if (options === void 0) {
        options = {}
      }
      this.canvas = canvas
      this.options = options
      this._handleMouseDown = function (event) {
        if (event.which === 1) {
          _this._mouseButtonDown = true
          _this._strokeBegin(event)
        }
      }
      this._handleMouseMove = function (event) {
        if (_this._mouseButtonDown) {
          _this._strokeMoveUpdate(event)
        }
      }
      this._handleMouseUp = function (event) {
        if (event.which === 1 && _this._mouseButtonDown) {
          _this._mouseButtonDown = false
          _this._strokeEnd(event)
        }
      }
      this._handleTouchStart = function (event) {
        event.preventDefault()
        if (event.targetTouches.length === 1) {
          const touch = event.changedTouches[0]
          _this._strokeBegin(touch)
        }
      }
      this._handleTouchMove = function (event) {
        event.preventDefault()
        const touch = event.targetTouches[0]
        _this._strokeMoveUpdate(touch)
      }
      this._handleTouchEnd = function (event) {
        const wasCanvasTouched = event.target === _this.canvas
        if (wasCanvasTouched) {
          event.preventDefault()
          const touch = event.changedTouches[0]
          _this._strokeEnd(touch)
        }
      }
      this.velocityFilterWeight = options.velocityFilterWeight || 0.7
      this.minWidth = options.minWidth || 0.5
      this.maxWidth = options.maxWidth || 2.5
      this.throttle = 'throttle' in options ? options.throttle : 16
      this.minDistance = 'minDistance' in options ? options.minDistance : 5
      this.dotSize =
        options.dotSize ||
        function dotSize() {
          return (this.minWidth + this.maxWidth) / 2
        }
      this.penColor = options.penColor || 'black'
      this.backgroundColor = options.backgroundColor || 'rgba(0,0,0,0)'
      this.onBegin = options.onBegin
      this.onEnd = options.onEnd
      this._strokeMoveUpdate = this.throttle
        ? throttle(SignaturePad.prototype._strokeUpdate, this.throttle)
        : SignaturePad.prototype._strokeUpdate
      this._ctx = canvas.getContext('2d')
      this.clear()
      this.on()
    }
    SignaturePad.prototype.clear = function () {
      const _a = this
      const ctx = _a._ctx
      const { canvas } = _a
      ctx.fillStyle = this.backgroundColor
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      this._data = []
      this._reset()
      this._isEmpty = true
    }
    SignaturePad.prototype.fromDataURL = function (dataUrl, options, callback) {
      const _this = this
      if (options === void 0) {
        options = {}
      }
      const image = new Image()
      const ratio = options.ratio || window.devicePixelRatio || 1
      const width = options.width || this.canvas.width / ratio
      const height = options.height || this.canvas.height / ratio
      this._reset()
      image.onload = function () {
        _this._ctx.drawImage(image, 0, 0, width, height)
        if (callback) {
          callback()
        }
      }
      image.onerror = function (error) {
        if (callback) {
          callback(error)
        }
      }
      image.src = dataUrl
      this._isEmpty = false
    }
    SignaturePad.prototype.toDataURL = function (type, encoderOptions) {
      if (type === void 0) {
        type = 'image/png'
      }
      switch (type) {
        case 'image/svg+xml':
          return this._toSVG()
        default:
          return this.canvas.toDataURL(type, encoderOptions)
      }
    }
    SignaturePad.prototype.on = function () {
      this.canvas.style.touchAction = 'none'
      this.canvas.style.msTouchAction = 'none'
      if (window.PointerEvent) {
        this._handlePointerEvents()
      } else {
        this._handleMouseEvents()
        if ('ontouchstart' in window) {
          this._handleTouchEvents()
        }
      }
    }
    SignaturePad.prototype.off = function () {
      this.canvas.style.touchAction = 'auto'
      this.canvas.style.msTouchAction = 'auto'
      this.canvas.removeEventListener('pointerdown', this._handleMouseDown)
      this.canvas.removeEventListener('pointermove', this._handleMouseMove)
      document.removeEventListener('pointerup', this._handleMouseUp)
      this.canvas.removeEventListener('mousedown', this._handleMouseDown)
      this.canvas.removeEventListener('mousemove', this._handleMouseMove)
      document.removeEventListener('mouseup', this._handleMouseUp)
      this.canvas.removeEventListener('touchstart', this._handleTouchStart)
      this.canvas.removeEventListener('touchmove', this._handleTouchMove)
      this.canvas.removeEventListener('touchend', this._handleTouchEnd)
    }
    SignaturePad.prototype.isEmpty = function () {
      return this._isEmpty
    }
    SignaturePad.prototype.fromData = function (pointGroups) {
      const _this = this
      this.clear()
      this._fromData(
        pointGroups,
        (_a) => {
          const { color } = _a
          const { curve } = _a
          return _this._drawCurve({ color, curve })
        },
        (_a) => {
          const { color } = _a
          const { point } = _a
          return _this._drawDot({ color, point })
        },
      )
      this._data = pointGroups
    }
    SignaturePad.prototype.toData = function () {
      return this._data
    }
    SignaturePad.prototype._strokeBegin = function (event) {
      const { options } = this
      window.timer = setInterval(() => {
        const lastPoint =
          window.lastPoints.length > 0 &&
          window.lastPoints[lastPoints.length - 1]
        window.timerPoint({ wrapper: options.wrapper, data: lastPoint })
      }, window.interval)
      window.mouseClickCnt[options.wrapper]++

      const newPointGroup = {
        color: this.penColor,
        points: [],
      }
      if (typeof this.onBegin === 'function') {
        this.onBegin(event)
      }
      this._data.push(newPointGroup)
      this._reset()
      this._strokeUpdate(event)
    }
    SignaturePad.prototype._strokeUpdate = function (event) {
      if (this._data.length === 0) {
        this._strokeBegin(event)
        return
      }
      const x = event.clientX
      const y = event.clientY
      const point = this._createPoint(x, y)
      const lastPointGroup = this._data[this._data.length - 1]
      const lastPoints = lastPointGroup.points
      const lastPoint =
        lastPoints.length > 0 && lastPoints[lastPoints.length - 1]
      const isLastPointTooClose = lastPoint
        ? point.distanceTo(lastPoint) <= this.minDistance
        : false
      const { color } = lastPointGroup

      window.lastPoints = lastPoints

      if (!lastPoint || !(lastPoint && isLastPointTooClose)) {
        // console.log(angle(lastPoint.x, lastPoint.y, point.x, point.y));
        // console.log(lastPoints);

        const curve = this._addPoint(point)

        // console.log(event.pointerType)
        if (event.pointerType === 'pen' && curve) {
          curve.startWidth = event.pressure * curve.startWidth
          curve.endWidth = event.pressure * curve.endWidth
          //                    console.log(event.pressure);
          // curve.endWidth = e.pre
        }

        if (curve && window.widthEvent) {
          window.widthEvent({
            wrapper: this.options.wrapper,
            data: curve.startWidth,
          })
        }

        if (!lastPoint) {
          point.width = this._drawDot({ color, point })
          var a1 = {
            time: point.time,
            width: 1,
            x: point.x,
            y: point.y,
            pressure: event.pressure,
            startPoint: 1,
          }
          window.catchPoint({ wrapper: this.options.wrapper, data: a1 })
        } else if (curve) {
          var a1 = {
            time: point.time,
            width: 1,
            x: curve.startPoint.x,
            y: curve.startPoint.y,
            pressure: event.pressure,
            startPoint: 0,
          }
          window.catchPoint({ wrapper: this.options.wrapper, data: a1 })
          const a2 = {
            time: point.time,
            width: 1,
            x: curve.endPoint.x,
            y: curve.endPoint.y,
            pressure: event.pressure,
            startPoint: 0,
          }
          window.catchPoint({ wrapper: this.options.wrapper, data: a2 })
          point.width = this._drawCurve({ color, curve })
        }
        lastPoints.push({
          time: point.time,
          width: point.width,
          x: point.x,
          y: point.y,
          pressure: event.pressure,
        })
      }
    }
    SignaturePad.prototype._strokeEnd = function (event) {
      clearInterval(window.timer)

      this._strokeUpdate(event)
      if (typeof this.onEnd === 'function') {
        this.onEnd(event)
      }
    }
    SignaturePad.prototype._handlePointerEvents = function () {
      this._mouseButtonDown = false
      this.canvas.addEventListener('pointerdown', this._handleMouseDown)
      this.canvas.addEventListener('pointermove', this._handleMouseMove)
      document.addEventListener('pointerup', this._handleMouseUp)
    }
    SignaturePad.prototype._handleMouseEvents = function () {
      this._mouseButtonDown = false
      this.canvas.addEventListener('mousedown', this._handleMouseDown)
      this.canvas.addEventListener('mousemove', this._handleMouseMove)
      document.addEventListener('mouseup', this._handleMouseUp)
    }
    SignaturePad.prototype._handleTouchEvents = function () {
      this.canvas.addEventListener('touchstart', this._handleTouchStart)
      this.canvas.addEventListener('touchmove', this._handleTouchMove)
      this.canvas.addEventListener('touchend', this._handleTouchEnd)
    }
    SignaturePad.prototype._reset = function () {
      this._lastPoints = []
      this._lastVelocity = 0
      this._lastWidth = (this.minWidth + this.maxWidth) / 2
      this._ctx.fillStyle = this.penColor
    }
    SignaturePad.prototype._createPoint = function (x, y) {
      const rect = this.canvas.getBoundingClientRect()
      return new Point(x - rect.left, y - rect.top, new Date().getTime())
    }
    SignaturePad.prototype._addPoint = function (point) {
      const { _lastPoints } = this
      _lastPoints.push(point)
      if (_lastPoints.length > 2) {
        if (_lastPoints.length === 3) {
          _lastPoints.unshift(_lastPoints[0])
        }
        const widths = this._calculateCurveWidths(
          _lastPoints[1],
          _lastPoints[2],
        )
        const curve = Bezier.fromPoints(_lastPoints, widths)
        _lastPoints.shift()
        return curve
      }
      return null
    }
    SignaturePad.prototype._calculateCurveWidths = function (
      startPoint,
      endPoint,
    ) {
      const velocity =
        this.velocityFilterWeight * endPoint.velocityFrom(startPoint) +
        (1 - this.velocityFilterWeight) * this._lastVelocity
      const newWidth = this._strokeWidth(velocity)
      const widths = {
        end: newWidth,
        start: this._lastWidth,
      }
      this._lastVelocity = velocity
      this._lastWidth = newWidth
      return widths
    }
    SignaturePad.prototype._strokeWidth = function (velocity) {
      return Math.max(this.maxWidth / (velocity + 1), this.minWidth)
    }
    SignaturePad.prototype._drawCurveSegment = function (x, y, width) {
      const ctx = this._ctx
      ctx.moveTo(x, y)
      ctx.arc(x, y, width, 0, 2 * Math.PI, false)
      this._isEmpty = false
    }
    SignaturePad.prototype._drawCurve = function (_a) {
      const { color } = _a
      const { curve } = _a
      const ctx = this._ctx
      const widthDelta = curve.endWidth - curve.startWidth
      const drawSteps = Math.floor(curve.length()) * 2
      ctx.beginPath()
      ctx.fillStyle = color

      for (let i = 0; i < drawSteps; i += 1) {
        const t = i / drawSteps
        const tt = t * t
        const ttt = tt * t
        const u = 1 - t
        const uu = u * u
        const uuu = uu * u
        let x = uuu * curve.startPoint.x
        x += 3 * uu * t * curve.control1.x
        x += 3 * u * tt * curve.control2.x
        x += ttt * curve.endPoint.x
        let y = uuu * curve.startPoint.y
        y += 3 * uu * t * curve.control1.y
        y += 3 * u * tt * curve.control2.y
        y += ttt * curve.endPoint.y
        const width = Math.min(
          curve.startWidth + ttt * widthDelta,
          this.maxWidth,
        )
        this._drawCurveSegment(x, y, width)
      }
      ctx.closePath()
      ctx.fill()

      return curve.startWidth
    }
    SignaturePad.prototype._drawDot = function (_a) {
      const { color } = _a
      const { point } = _a
      const ctx = this._ctx
      const width =
        typeof this.dotSize === 'function' ? this.dotSize() : this.dotSize
      ctx.beginPath()
      this._drawCurveSegment(point.x, point.y, width)
      ctx.closePath()
      ctx.fillStyle = color
      ctx.fill()

      return width
    }
    SignaturePad.prototype._fromData = function (
      pointGroups,
      drawCurve,
      drawDot,
    ) {
      for (
        let _i = 0, pointGroups_1 = pointGroups;
        _i < pointGroups_1.length;
        _i++
      ) {
        const group = pointGroups_1[_i]
        const { color } = group
        const { points } = group
        if (points.length > 1) {
          for (let j = 0; j < points.length; j += 1) {
            const basicPoint = points[j]
            const point = new Point(basicPoint.x, basicPoint.y, basicPoint.time)
            this.penColor = color
            if (j === 0) {
              this._reset()
            }
            const curve = this._addPoint(point)
            if (curve) {
              drawCurve({ color, curve })
            }
          }
        } else {
          this._reset()
          drawDot({
            color,
            point: points[0],
          })
        }
      }
    }
    SignaturePad.prototype._toSVG = function () {
      const _this = this
      const pointGroups = this._data
      const ratio = Math.max(window.devicePixelRatio || 1, 1)
      const minX = 0
      const minY = 0
      const maxX = this.canvas.width / ratio
      const maxY = this.canvas.height / ratio
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      svg.setAttribute('width', this.canvas.width.toString())
      svg.setAttribute('height', this.canvas.height.toString())
      this._fromData(
        pointGroups,
        (_a) => {
          const { color } = _a
          const { curve } = _a
          const path = document.createElement('path')
          if (
            !isNaN(curve.control1.x) &&
            !isNaN(curve.control1.y) &&
            !isNaN(curve.control2.x) &&
            !isNaN(curve.control2.y)
          ) {
            const attr =
              `M ${curve.startPoint.x.toFixed(3)},${curve.startPoint.y.toFixed(
                3,
              )} ` +
              `C ${curve.control1.x.toFixed(3)},${curve.control1.y.toFixed(
                3,
              )} ${curve.control2.x.toFixed(3)},${curve.control2.y.toFixed(
                3,
              )} ${curve.endPoint.x.toFixed(3)},${curve.endPoint.y.toFixed(3)}`
            path.setAttribute('d', attr)
            path.setAttribute(
              'stroke-width',
              (curve.endWidth * 2.25).toFixed(3),
            )
            path.setAttribute('stroke', color)
            path.setAttribute('fill', 'none')
            path.setAttribute('stroke-linecap', 'round')
            svg.appendChild(path)
          }
        },
        (_a) => {
          const { color } = _a
          const { point } = _a
          const circle = document.createElement('circle')
          const dotSize =
            typeof _this.dotSize === 'function'
              ? _this.dotSize()
              : _this.dotSize
          circle.setAttribute('r', dotSize.toString())
          circle.setAttribute('cx', point.x.toString())
          circle.setAttribute('cy', point.y.toString())
          circle.setAttribute('fill', color)
          svg.appendChild(circle)
        },
      )
      const prefix = 'data:image/svg+xml;base64,'
      const header =
        `${
          '<svg' +
          ' xmlns="http://www.w3.org/2000/svg"' +
          ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        }` +
        ` viewBox="${minX} ${minY} ${maxX} ${maxY}"` +
        ` width="${maxX}"` +
        ` height="${maxY}"` +
        `>`
      let body = svg.innerHTML
      if (body === undefined) {
        const dummy = document.createElement('dummy')
        const nodes = svg.childNodes
        dummy.innerHTML = ''
        for (let i = 0; i < nodes.length; i += 1) {
          dummy.appendChild(nodes[i].cloneNode(true))
        }
        body = dummy.innerHTML
      }
      const footer = '</svg>'
      const data = header + body + footer
      return prefix + btoa(data)
    }
    return SignaturePad
  })()

  return SignaturePad
})
// # sourceMappingURL=signature_pad.umd.js.map
