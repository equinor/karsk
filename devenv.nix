{
  ...
}:

{
  languages.python = {
    enable = true;
    uv.enable = true;
    uv.sync.enable = true;
    venv.enable = true;
  };

  # Use system git rather than Nix' because of code signing shenanigans on macOS
  env.KARSK_GIT = "/usr/bin/git";
}
