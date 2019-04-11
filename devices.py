import subprocess

class Devices:
  """
  Get a list of all available video devices.

  @return: Returns a list of video devices.
  """
  def get():
    devices = subprocess.check_output('ls -h /dev/video*', shell = True)
    devices = str(devices).replace("b'", '').replace("'", '').split('\\n')
    devices = list(filter(None, devices))

    return devices
