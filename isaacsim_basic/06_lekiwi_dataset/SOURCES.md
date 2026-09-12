# 6편 출처와 화면 기록

## 공식 문서

- [Isaac Sim 5.1 물리 기초](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html)
- [로봇 Python 시작 예제](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/introduction/quickstart_isaacsim_robot.html)
- [관절 제어 API](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html)
- [카메라 센서](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html)
- [Hugging Face Hub 폴더 업로드](https://huggingface.co/docs/huggingface_hub/main/en/guides/upload)
- [HfApi 토큰 직접 전달](https://huggingface.co/docs/huggingface_hub/main/en/package_reference/hf_api)
- [Hugging Face 사용자 토큰 보안](https://huggingface.co/docs/hub/security-tokens)
- [ViewportWindow의 UI 표시 영역 get_frame](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.viewport.window/107.0.7/omni.kit.viewport.window/omni.kit.viewport.window.ViewportWindow.html)

문서를 참고해 프로젝트 교육용 예제를 직접 작성했습니다. 런타임 버전은 Isaac Sim 5.1.0입니다.
1~5장 학생 파일은 로봇 자산 없이 Isaac Sim Python으로 실행합니다. 6장은 프로젝트의 기록 형식과 로봇 자산을 사용합니다.

- [5.1 Replicator 비동기 렌더링과 프레임 누락](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/replicator_tutorials/troubleshooting.html#async-rendering-and-frame-skipping)

- [5.1 렌더 프레임 지연과 동기 설정](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/python_scripting/util_snippets.html#rendering-frame-delay)

## 화면

2026-09-10 코드 실습 개편: 전용 Lesson 탭을 사용하지 않는 실제 Isaac Sim 화면을 캡처합니다.
원본은 images/screenshots, 빨간 표시 좌표와 설명은 images/annotations.json,
원본을 포함한 표시본은 SVG·PNG입니다. 코드는 Markdown 코드 블록으로 제시합니다.
기존 비교 사진은 과거 검증 자료일 수 있으며 현재 실행 안내는 README에 명시된 화면을 따릅니다.

2026-09-11 `images/10-recording-status.png`: 서버에서 실행한 6장 실습의 WebRTC 화면에서 두 Viewport 영역을 직접 캡처했습니다.
실제 리더를 연결하지 않은 표시 검사이며, 빨간 수집 상태·에피소드 시간·프레임 수를 확인하는 예시입니다. 카메라 원본 영상에는 이 UI가 포함되지 않습니다.

[교재로 돌아가기](README.md)

2026-09-12 `images/11-browser-dataset.png`: 노트북 Chrome의 실제 브라우저 VS Code 화면을 캡처했습니다.
서버의 `03_convert_dataset.py`에서 에피소드·이름을 수정해 저장한 뒤 파일만 실행하고, `04_inspect_dataset.py`로 재검사한 결과입니다.
1개 에피소드·422프레임·30 FPS, LeRobot v3 변환과 재열기를 확인했습니다. 커서가 설정과 결과를 가리지 않는지 확인했습니다.
