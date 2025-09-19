awk '{
  if (NR % 10 == 1) {
    cmd = "python3 safaribooks.py"  # Replace with your actual command
  }
  cmd = cmd " \"" $0 "\""
  if (NR % 10 == 0) {
    system(cmd)
  }
}
END {
  if (NR % 10 != 0) {
    system(cmd)
  }
}' books2.txt