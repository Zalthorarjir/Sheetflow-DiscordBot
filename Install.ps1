Start-Process winget -ArgumentList 'install -e --id Python.Python.3.11' -Wait
Start-Process python -ArgumentList '--version' -Wait
Start-Process pip -ArgumentList 'install discord.py' -Wait
Start-Process pip -ArgumentList 'install python-dotenv' -Wait

# Importing the discord module and printing its version
python -c "import discord; print(discord.__version__)"

# Display a message when done
Write-Host "All tasks are completed successfully."