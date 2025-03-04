/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { onMounted, useState, useRef, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FaceIdRecognitionDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        
        this.title = _t("Face ID Recognition");

        this.videoRef = useRef("video");
        this.imageRef = useRef("image");
        this.canvasRef = useRef("canvas");
        this.selectRef = useRef("select");

        this.notificationService = useService('notification');

        this.state = useState({
          videoElwidth: 0,
          videoElheight: 0,
          intervalID: false,
          match_employee_id : false,
          is_update_login: false,
          isInit: false,

          blink : {
            start: 0,
            end: 0,
            time: 0,
          },
          matchOptions : { 
            order: 2, 
            multiplier: 25, 
            min: 0.2, 
            max: 0.8 
          },
          humanOptions : {
            minConfidence: 0.6, // overal face confidence for box, face, gender, real, live
            minSize: 224, // min input to face descriptor model before degradation
            maxTime: 30000, // max time before giving up
            blinkMin: 10, // minimum duration of a valid blink
            blinkMax: 800, // maximum duration of a valid blink
            threshold: 0.5, // minimum similarity
            distanceMin: 0.4, // closest that face is allowed to be to the cammera in cm
            distanceMax: 1.0, // farthest that face is allowed to be to the cammera in cm
            mask: false,
            rotation: false,
          },
          ok : {
            faceCount: { status: false, val: 0 },
            faceConfidence: { status: false, val: 0 },
            facingCenter: { status: false, val: 0 },
            lookingCenter: { status: false, val: 0 },
            blinkDetected: { status: false, val: 0 },
            faceSize: { status: false, val: 0 },
            antispoofCheck: { status: false, val: 0 },
            livenessCheck: { status: false, val: 0 },
            distance: { status: false, val: 0 },
            age: { status: false, val: 0 },
            gender: { status: false, val: 0 },
            timeout: { status: true, val: 0 },
            descriptor: { status: false, val: 0 },
            elapsedMs: { status: undefined, val: 0 }, // total time while waiting for valid face
            detectFPS: { status: undefined, val: 0 }, // mark detection fps performance
            drawFPS: { status: undefined, val: 0 }, // mark redraw fps performance
          },

          timestamp : { 
            detect: 0, 
            draw: 0 
          },
          startTime : 0,
        })
        
        this.descriptors = this.props.labeledFaceDescriptors;
        onMounted(async () => {
            await this.loadWebcam();            
        });  
    }
    loadWebcam(){
        var self = this;
        if (navigator.mediaDevices) {            
            var videoElement = this.videoRef.el;
            var videoSelect =this.selectRef.el;
            const selectors = [videoSelect]

            startStream();

            videoSelect.onchange = startStream;
            navigator.mediaDevices.enumerateDevices().then(gotDevices).catch(handleError);

            function startStream() {
                if (window.stream) {
                  window.stream.getTracks().forEach(track => {
                    track.stop();
                  });
                }
                const videoSource = videoSelect.value;
                const constraints = {
                  video: {deviceId: videoSource ? {exact: videoSource} : undefined}
                };
                navigator.mediaDevices.getUserMedia(constraints).then(gotStream).then(gotDevices).catch(handleError);
            }

            function gotStream(stream) {
                window.stream = stream; // make stream available to console
                videoElement.srcObject = stream;
                // Refresh button list in case labels have become available
                videoElement.onloadedmetadata = function(e) {
                    videoElement.play().then(function(){
                      self.detectionLoop();
                      self.drawLoop();
                    });
                    self.state.videoElwidth = videoElement.offsetWidth;
                    self.state.videoElheight = videoElement.offsetHeight;
                };
                return navigator.mediaDevices.enumerateDevices();
            }

            function gotDevices(deviceInfos) {
                // Handles being called several times to update labels. Preserve values.
                const values = selectors.map(select => select.value);
                selectors.forEach(select => {
                  while (select.firstChild) {
                    select.removeChild(select.firstChild);
                  }
                });
                for (let i = 0; i !== deviceInfos.length; ++i) {
                  const deviceInfo = deviceInfos[i];
                  const option = document.createElement('option');
                  option.value = deviceInfo.deviceId;
                  if (deviceInfo.kind === 'videoinput') {
                    option.text = deviceInfo.label || `camera ${videoSelect.length + 1}`;
                    videoSelect.appendChild(option);
                  } 
                  else {
                    // console.log('Some other kind of source/device: ', deviceInfo);
                  }
                }
                selectors.forEach((select, selectorIndex) => {
                  if (Array.prototype.slice.call(select.childNodes).some(n => n.value === values[selectorIndex])) {
                    select.value = values[selectorIndex];
                  }
                });
            }
            
            function handleError(error) {
                console.log('navigator.MediaDevices.getUserMedia error: ', error.message, error.name);
            }               
        }
        else{
            this.notificationService.add(
              _t("https Failed: Warning! WEBCAM MAY ONLY WORKS WITH HTTPS CONNECTIONS. So your Odoo instance must be configured in https mode."), 
              { type: "danger" });
        }
    }
    isAllOk(){
      return this.state.ok.faceCount.status
          && this.state.ok.faceSize.status
          && (this.props.configParams.human_blinkdetection ? this.state.ok.blinkDetected.status : true)
          && (this.props.configParams.human_facingcenter ? this.state.ok.facingCenter.status : true)
          && (this.props.configParams.human_lookingcenter ? this.state.ok.lookingCenter.status : true)
          && this.state.ok.faceConfidence.status
          && (this.props.configParams.human_antispoofcheck ? this.state.ok.antispoofCheck.status : true)
          && (this.props.configParams.human_livenesscheck ? this.state.ok.livenessCheck.status : true)
          && this.state.ok.distance.status
          && this.state.ok.descriptor.status
          && this.state.ok.age.status
          && this.state.ok.gender.status;
    }
    async detectionLoop() {
      var self = this;
      var canvas =self.canvasRef.el;

      if (!canvas) {
          return;
      }

      return new Promise(function(resolve){
          self.detectionTimeout = setTimeout(function(){
              if(!self.state.isInit){
                  self.detectionLoop();
                  resolve();
              }                    
          });
      });
    }
    async drawLoop() {
      var self = this;

      var video = self.videoRef.el;
      var canvas =self.canvasRef.el;
      
      if (!canvas) {
          return;
      }

      canvas.width = self.state.videoElwidth;
      canvas.height = self.state.videoElheight;
      
      var ctx = canvas.getContext('2d');
      
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      if (!video.paused) {
        const detect = await self.props.human.detect(canvas);
        await self.props.human.draw.all(canvas, detect);
        
        const now = self.props.human.now();
        self.state.ok.drawFPS.val = Math.round(10000 / (now - self.state.timestamp.draw)) / 10;
        self.state.timestamp.draw = now;

        self.state.ok.faceCount.val = self.props.human.result.face.length;
        self.state.ok.faceCount.status = self.state.ok.faceCount.val === 1; // must be exactly detected face

        //Validating Face
        if (self.state.ok.faceCount.status){
            const gestures = Object.values(self.props.human.result.gesture).map((gesture) => gesture.gesture);
            if (gestures.includes('blink left eye') || gestures.includes('blink right eye')) {
                self.state.blink.start = self.props.human.now();
            }

            if (self.state.blink.start > 0 && !gestures.includes('blink left eye') && !gestures.includes('blink right eye')) {
                self.state.blink.end = self.props.human.now();
            }
            self.state.ok.blinkDetected.status = self.state.ok.blinkDetected.status || (Math.abs(self.state.blink.end - self.state.blink.start) > self.state.humanOptions.blinkMin && Math.abs(self.state.blink.end - self.state.blink.start) < self.state.humanOptions.blinkMax);
            if (self.state.ok.blinkDetected.status && self.state.blink.time === 0) {
                self.state.blink.time = Math.trunc(self.state.blink.end - self.state.blink.start);
            }

            self.state.ok.facingCenter.status = gestures.includes('facing center');
            self.state.ok.lookingCenter.status = gestures.includes('looking center'); // must face camera and look at camera

            self.state.ok.faceConfidence.val = self.props.human.result.face[0].faceScore || self.props.human.result.face[0].boxScore || 0;
            self.state.ok.faceConfidence.status = self.state.ok.faceConfidence.val >= self.state.humanOptions.minConfidence;

            self.state.ok.antispoofCheck.val = self.props.human.result.face[0].real || 0;
            self.state.ok.antispoofCheck.status = self.state.ok.antispoofCheck.val >= self.state.humanOptions.minConfidence;

            self.state.ok.livenessCheck.val = self.props.human.result.face[0].live || 0;
            self.state.ok.livenessCheck.status = self.state.ok.livenessCheck.val >= self.state.humanOptions.minConfidence;
            self.state.ok.faceSize.val = Math.min(self.props.human.result.face[0].box[2], self.props.human.result.face[0].box[3]);
            self.state.ok.faceSize.status = self.state.ok.faceSize.val >= self.state.humanOptions.minSize;
            self.state.ok.distance.val = self.props.human.result.face[0].distance || 0;
            self.state.ok.distance.status = (self.state.ok.distance.val >= self.state.humanOptions.distanceMin) && (self.state.ok.distance.val <= self.state.humanOptions.distanceMax);
            self.state.ok.descriptor.val = self.props.human.result.face[0].embedding?.length || 0;
            self.state.ok.descriptor.status = self.state.ok.descriptor.val > 0;
            self.state.ok.age.val = self.props.human.result.face[0].age || 0;
            self.state.ok.age.status = self.state.ok.age.val > 0;
            self.state.ok.gender.val = self.props.human.result.face[0].genderScore || 0;
            self.state.ok.gender.status = self.state.ok.gender.val >= self.state.humanOptions.minConfidence;
        }

        self.state.ok.timeout.status = self.state.ok.elapsedMs.val <= self.state.humanOptions.maxTime;   
        if (self.isAllOk()) {//|| !self.ok.timeout.status   
            await self.detectionFace(detect);
        } 
        self.state.ok.elapsedMs.val = Math.trunc(self.props.human.now() - self.startTime);
      }

      return new Promise(function(resolve){
          self.drawTimeout = setTimeout(function(){
              if(!self.state.isInit){
                  self.drawLoop();
                  resolve();
              }
          },30);
      });
    }

    async detectionFace(detect) {
          var self = this;          
          if (detect && detect.face) {
              for (var face of detect.face) {
                  const descriptor = await self.descriptors.map((rec) => rec.descriptor).filter((desc) => desc.length > 0);
                  const match = await self.props.human.match.find(face.embedding, descriptor, self.state.matchOptions);
                  var similarity = parseInt(this.props.configParams.human_similarity) || 50;
                  if ((match.similarity * 100).toFixed(2) >= similarity) {
                        self.props.human.tf.dispose(face.tensor);
                        var descriptor_id = self.descriptors[match.index].descriptor_id;
                        var login = self.descriptors[match.index].login;
                        self.updaterecognition(login,descriptor_id);
                        return 'break';
                  }
                  self.props.human.tf.dispose(face.tensor);
              }
          }
    }

    onClose() {
      var self = this;
      if (window.stream) {
        window.stream.getTracks().forEach(track => {
          track.stop();
        });
      }
      self.props.close && self.props.close();
    }

    async updaterecognition(login,descriptor_id){
      var self = this;
      if (!self.state.is_update_login) {
          self.state.is_update_login = true;
          return this.rpc('/web/login/faceid_auth',{
              'login': login,
              'descriptor_id': descriptor_id,
          }).then(function (response) {
              console.log(response);
              if (response && response.login_success){
                  window.location.replace(response.url);
                  self.props.close();
              }else{
                self.notificationService.add(_t("Detection Failed: User not found, Please add your face ID to user profile."), {
                  type: "danger",
                });
                self.props.close();
              }                    
          });                
      }
    }
}
FaceIdRecognitionDialog.components = { Dialog };
FaceIdRecognitionDialog.template = "faceid_authentication.FaceIdRecognitionDialog";
FaceIdRecognitionDialog.defaultProps = {};
FaceIdRecognitionDialog.props = {
  human: Object,
  configParams: Object,
  labeledFaceDescriptors : Object,
}
