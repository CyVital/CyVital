# Architecture Overview

This document provides a high-level overview of the architecture of the CyVital project. It outlines the primary layers, key data flows, and operational notes necessary to understand the system's operation and extension points.

## Layers

### 1. GUI - /src/gui
The Graphical User Interface (GUI) is the entry point for users to interact with the system. It provides visualizations and controls for operating the sensor modules and viewing data plots.
`src/gui/tkGui.py` creates a plain `tk.Tk` window, embeds single Matplotlib w/ `FigureCanvasTkAgg`, and wires a `FuncAnimation` loop to update the reaction-time plot making it "live"

### 2. Sensor Modules - /src/gui/sensors
The sensor modules are responsible for collecting data from various sensors. Each module can be added or removed to extend functionality.

### 3. Plots - /src/plots
Plots visualize data collected from sensors, allowing users to analyze trends and correlations in real time.

### 4. Scope - /src/oscilloscope
Scope defines the oscilloscope in use to collect the data.

## Key Data Flow

### SensorUpdate
Sensor updates represent the data collected at regular intervals from sensors, which are then processed by the plotting mechanism.

### SensorDefinition
This component defines the characteristics of each sensor module, including communication protocols and data formats.

## CyVital.spec
This file is used to compile the PyInstaller executables/apps, using the icons in the /icons folder. Just type `python PyInstaller CyVital.spec` to run.

## /icons
This folder holds the icons used in genderating the executables
