import SwiftUI

public struct SidebarView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Brand Logo Header (Clean bold typography, no emoji)
            VStack(alignment: .leading, spacing: 2) {
                Text("FOCUS")
                    .font(.system(size: 22, weight: .heavy, design: .rounded))
                    .tracking(2)
                    .foregroundColor(.primary)

                Text("AI VIDEO STUDIO")
                    .font(.system(size: 9, weight: .bold))
                    .tracking(1.5)
                    .foregroundColor(appState.accentColor)
            }
            .padding(.horizontal, 14)
            .padding(.top, 14)

            Divider()
                .padding(.horizontal, 10)

            // Section 1: Workflow
            VStack(alignment: .leading, spacing: 4) {
                Text(appState.localized("workflow"))
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 14)

                SidebarItem(
                    title: appState.localized("tab_generator"),
                    icon: "wand.and.stars",
                    isSelected: appState.currentTab == .generator,
                    accentColor: appState.accentColor
                ) {
                    appState.currentTab = .generator
                }

                SidebarItem(
                    title: appState.localized("tab_gallery"),
                    icon: "person.crop.artframe",
                    isSelected: appState.currentTab == .gallery,
                    accentColor: appState.accentColor
                ) {
                    appState.currentTab = .gallery
                }
            }

            // Section 2: Resources
            VStack(alignment: .leading, spacing: 4) {
                Text(appState.localized("resources"))
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 14)

                SidebarItem(
                    title: appState.localized("tab_preferences"),
                    icon: "gearshape.2",
                    isSelected: appState.currentTab == .settings,
                    accentColor: appState.accentColor
                ) {
                    appState.currentTab = .settings
                }

                SidebarItem(
                    title: appState.localized("tab_logs"),
                    icon: "terminal",
                    isSelected: appState.currentTab == .logs,
                    accentColor: appState.accentColor
                ) {
                    appState.currentTab = .logs
                }
            }

            Spacer()

            // Version Badge Footer
            HStack {
                Text("v2.0.0 (macOS Native)")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(.secondary)
                Spacer()
                Circle()
                    .fill(appState.isProcessing ? Color.orange : Color.green)
                    .frame(width: 8, height: 8)
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 12)
        }
        .frame(minWidth: 200, maxWidth: 220)
        .background(.ultraThinMaterial)
    }
}

struct SidebarItem: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let accentColor: Color
    let action: () -> Void
    @State private var isHovered: Bool = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(isSelected ? .white : (isHovered ? .primary : .secondary))
                    .frame(width: 18)

                Text(title)
                    .font(.system(size: 12, weight: isSelected ? .semibold : .regular))
                    .foregroundColor(isSelected ? .white : .primary)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .contentShape(Rectangle()) // Makes the entire row hit-testable
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(isSelected ? accentColor : (isHovered ? Color.white.opacity(0.08) : Color.clear))
            )
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 8)
        .onHover { h in
            isHovered = h
        }
    }
}
