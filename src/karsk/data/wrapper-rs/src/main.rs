mod util;
mod versions;

use std::env::{args, args_os, current_exe};
use std::ffi::OsString;
use std::io::{Write, stdout};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::util::exit;
use crate::versions::print_versions_to;

const DEFAULT_VERSION: &str = "stable";

#[derive(Debug, PartialEq, Eq)]
enum Action {
    PrintVersions,
    OsOutput(OsString),
    Command {
        program: PathBuf,
        args: Vec<OsString>,
        show_help: bool,
    },
    Error(String),
}

impl Action {
    fn parse_version_arg(args: &[OsString], pos: usize) -> Option<OsString> {
        // A version name cannot start with a hypen (-) to avoid confusing them for args.
        args.get(pos)
            .cloned()
            .filter(|arg| arg.as_bytes().first() != Some(&b'-'))
    }

    pub fn parse_args(
        versions_dir: impl AsRef<Path>,
        program: OsString,
        args: &[OsString],
    ) -> Action {
        let versions_dir = versions_dir.as_ref();
        let mut show_help: bool = false;
        let mut version: OsString = DEFAULT_VERSION.into();

        let mut pos: usize = 0;
        if let Some(arg1) = args.get(pos).and_then(|s| s.to_str()) {
            match arg1 {
                "-h" | "--help" => {
                    show_help = true;
                }
                "--print-versions" => {
                    return Action::PrintVersions;
                }
                "-v" | "--version" => {
                    if let Some(v) = Action::parse_version_arg(args, pos + 1) {
                        version = v;
                        pos += 2;
                    };
                }
                "--print-version-path" => {
                    if let Some(v) = Action::parse_version_arg(args, pos + 1)
                        .map(|s| versions_dir.join(s))
                        .map(|p| p.into_os_string())
                    {
                        return Action::OsOutput(v);
                    }
                }
                _ => {}
            }
        }

        if !versions_dir.join(&version).exists() {
            return Action::Error(format!("[Karsk wrapper] No such version: {:?}", version));
        }

        let program = versions_dir.join(version).join("bin").join(program);

        Action::Command {
            program,
            args: args[pos..].to_owned(),
            show_help,
        }
    }
}

fn main() {
    let mut args = args_os();

    let executable = current_exe().expect("Couldn't obtain the wrapper's executable path");
    let program = args
        .next()
        .map(PathBuf::from)
        .and_then(|arg0| arg0.file_name().map(|s| s.to_os_string()))
        .expect("Couldn't obtain the wrapper's executable name");

    let versions_dir = executable
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.join("versions"))
        .expect("Couldn't determine 'versions' directory");

    match Action::parse_args(versions_dir.clone(), program, &args.collect::<Vec<_>>()) {
        Action::PrintVersions => {
            print_versions_to(versions_dir, &mut stdout());
        }
        Action::OsOutput(text) => {
            let _ = std::io::stdout().write(text.as_bytes());
        }
        Action::Command {
            program,
            args,
            show_help,
        } => {
            let mut command = Command::new(&program);
            if show_help {
                usage();
            }
            command.args(args);
            let err = command.exec();
            exit!(
                "[Karsk wrapper] Couldn't start program {:?}: {}",
                program,
                err
            );
        }
        Action::Error(msg) => {
            exit!("{}", msg);
        }
    }
}

fn usage() {
    let project_name = current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_owned())) // "[program]/bin/"
        .and_then(|p| p.parent().map(|p| p.to_owned())) // "[program]/"
        .and_then(|p| p.file_name().map(|s| s.to_owned()))
        .unwrap_or_else(|| OsString::from("the program"));

    println!(
        "Wrapper usage: {} [ARGS...]",
        args().next().unwrap_or_else(|| String::from(".wrapper"))
    );
    println!();
    println!("This program is built with Karsk which uses a version-aware wrapper.");
    println!(
        "Use the following arguments to modify which version of {:?} to run.",
        project_name
    );
    println!("See Karsk documentation for more information: https://equinor.github.io/karsk");
    println!();
    println!("    --help, -h            - Print this help message");
    println!("    --version, -v [NAME]  - Use a different version");
    println!("    --print-versions      - List available versions");
    println!();
}

#[cfg(test)]
mod tests {
    use std::fs::create_dir_all;
    use std::os::unix::fs::symlink;

    use super::*;
    use testdir::testdir;

    fn parse_args(tmpdir: impl AsRef<Path>, args: Vec<impl ToString>) -> Action {
        let tmpdir = tmpdir.as_ref();
        create_dir_all(tmpdir.join("versions/1.2.3/bin")).unwrap();
        symlink("/usr/bin/true", tmpdir.join("versions/1.2.3/bin/some-exec")).unwrap();
        symlink("1.2.3", tmpdir.join("versions/stable")).unwrap();

        let vargs: Vec<OsString> = args
            .into_iter()
            .map(|x| x.to_string())
            .map(|x| OsString::from(x))
            .collect();

        Action::parse_args(tmpdir.join("versions"), OsString::from("some-exec"), &vargs)
    }

    #[test]
    fn test_no_args() {
        let empty: Vec<String> = Vec::new();
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, empty);

        assert_eq!(
            action,
            Action::Command {
                program: tmpdir.join("versions/stable/bin/some-exec"),
                args: vec![],
                show_help: false,
            }
        );
    }

    #[test]
    fn test_version() {
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, vec!["--version"]);

        assert_eq!(
            action,
            Action::Command {
                program: tmpdir.join("versions/stable/bin/some-exec"),
                args: vec![OsString::from("--version")],
                show_help: false,
            }
        );
    }

    #[test]
    fn test_version_with_arg() {
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, vec!["--version", "1.2.3"]);

        assert_eq!(
            action,
            Action::Command {
                program: tmpdir.join("versions/1.2.3/bin/some-exec"),
                args: vec![],
                show_help: false,
            }
        );
    }

    #[test]
    fn test_version_with_arg_and_rest() {
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, vec!["--version", "1.2.3", "-fi", "fo", "--fum"]);

        assert_eq!(
            action,
            Action::Command {
                program: tmpdir.join("versions/1.2.3/bin/some-exec"),
                args: vec![
                    OsString::from("-fi"),
                    OsString::from("fo"),
                    OsString::from("--fum")
                ],
                show_help: false,
            }
        );
    }

    #[test]
    fn test_version_that_doesnt_exist() {
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, vec!["--version", "uh-oh"]);

        assert_eq!(
            action,
            Action::Error(String::from("[Karsk wrapper] No such version: \"uh-oh\""))
        );
    }

    #[test]
    fn test_version_followed_by_arg() {
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, vec!["--version", "--hello"]);

        assert_eq!(
            action,
            Action::Command {
                program: tmpdir.join("versions/stable/bin/some-exec"),
                args: vec![OsString::from("--version"), OsString::from("--hello")],
                show_help: false,
            }
        );
    }

    #[test]
    fn test_print_version_path() {
        let tmpdir = testdir!();
        let action = parse_args(&tmpdir, vec!["--print-version-path", "1.2.3"]);

        assert_eq!(
            action,
            Action::OsOutput(tmpdir.join("versions/1.2.3").into_os_string())
        );
    }
}
